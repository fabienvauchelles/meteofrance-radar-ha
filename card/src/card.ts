import { html, type TemplateResult } from "lit";
import { createRef } from "lit/directives/ref.js";
import { RadarApi } from "./api";
import {
  BasemapSource,
  buildViewModel,
  DEFAULT_HEIGHT,
  DEFAULT_WIDTH,
  languageTag,
  wantsFill,
} from "./card-data";
import { RadarCardHost } from "./card-host";
import { Compositor } from "./compositor";
import { type CardConfig, DEFAULTS, type ResolvedConfig, validateConfig } from "./config";
import { LayerLoader } from "./loader";
import { Playback } from "./playback";
import { buildPlaylist, EMPTY_PLAYLIST, type Playlist, restingIndex } from "./playlist";
import { buildSteps, findFrame, type Step, stepUrls, titleFrame } from "./timeline";
import {
  browserSeams,
  type CardSeams,
  type FramesResponse,
  type HomeAssistant,
  type PeriodName,
} from "./types";
import { type LoadState, renderCard } from "./view";

export const REFRESH_MS = 60_000;

export class MeteoFranceRadarCard extends RadarCardHost {
  /** Browser services; tests replace them before the card is connected. */
  seams: CardSeams = browserSeams();

  private _config?: ResolvedConfig;
  private _hass?: HomeAssistant;
  private _period: PeriodName = DEFAULTS.default_period;
  private _data: FramesResponse | null = null;
  private _playlist: Playlist = EMPTY_PLAYLIST;
  private _fill = false;
  private _state: LoadState = "loading";
  private _steps: Step[] = [];
  private _shown = 0;
  private _generation = 0;
  private _refreshTimer: number | null = null;
  private _resumeOnConnect = false;
  private readonly _basemap = new BasemapSource();
  private _compositor: Compositor | null = null;
  private readonly _canvasRef = createRef<HTMLCanvasElement>();
  private readonly _api = new RadarApi(() => this._hass);
  private readonly _loader = new LayerLoader({
    fetchBlob: (url) => this._api.blob(url),
    decode: (blob) => this.seams.createImageBitmap(blob),
  });
  private readonly _playback = new Playback(
    {
      steps: () => this._steps,
      render: (index, weight) => this._render(index, weight),
      ensure: (index) => this._ensure(index),
      changed: () => this.requestUpdate(),
    },
    {
      now: () => this.seams.now(),
      requestFrame: (callback) => this.seams.requestFrame(callback),
      cancelFrame: (handle) => this.seams.cancelFrame(handle),
    },
  );

  setConfig(config: CardConfig): void {
    const resolved = validateConfig(config);
    const periodChanged = this._config?.default_period !== resolved.default_period;
    this._config = resolved;
    this._fill = wantsFill(config);
    this._rebuild();
    if (periodChanged) {
      this._period = resolved.default_period;
      if (this.isConnected) void this._load();
    }
    this.requestUpdate();
  }

  set hass(hass: HomeAssistant) {
    const previous = this._hass;
    this._hass = hass;
    if (!previous && this.isConnected && !this._data) void this._load();
    if (
      languageTag(previous) !== languageTag(hass) ||
      previous?.config.time_zone !== hass.config.time_zone
    ) {
      this.requestUpdate();
    }
  }

  get hass(): HomeAssistant | undefined {
    return this._hass;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._refreshTimer = window.setInterval(() => void this._refresh(), REFRESH_MS);
    // Coming back to the view resumes a loop the user left playing.
    if (this._resumeOnConnect) this._playback.play();
    if (this._data) void this._refresh();
    else void this._load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._refreshTimer !== null) window.clearInterval(this._refreshTimer);
    this._refreshTimer = null;
    this._resumeOnConnect = this._playback.playing;
    this._playback.pause();
  }

  protected updated(): void {
    const canvas = this._canvasRef.value;
    if (!canvas) return;
    const width = this._data?.grid.width ?? DEFAULT_WIDTH;
    const height = this._data?.grid.height ?? DEFAULT_HEIGHT;
    if (this._compositor?.matches(canvas, width, height)) return;
    this._compositor = new Compositor(canvas, width, height, this.seams.context2d);
    this._compositor.setBasemap(this._basemap.bitmap);
    this._compositor.drawBasemap();
  }

  render(): TemplateResult {
    if (!this._config) return html``;
    const vm = buildViewModel({
      config: this._config,
      hass: this._hass,
      data: this._data,
      playlist: this._playlist,
      state: this._state,
      shown: this._shown,
      playing: this._playback.playing,
      waiting: this._playback.waiting,
      position: this._playback.stepIndex,
      stepCount: this._steps.length,
      period: this._period,
      fill: this._fill,
      panel: this.panel,
    });
    return renderCard(vm, {
      canvasRef: this._canvasRef,
      togglePlay: () => this._playback.toggle(),
      step: (delta) => void this._playback.stepBy(delta).catch(logLayerError),
      scrub: (index) => {
        this._shown = index;
        void this._playback.scrub(index).catch(logLayerError);
      },
      scrubEnd: () => this._playback.scrubEnd(),
      selectPeriod: (period) => this._selectPeriod(period),
    });
  }

  /** Rebuild the playlist and its timeline from the data and the config. */
  private _rebuild(): void {
    const config = this._config ?? DEFAULTS;
    this._playlist = buildPlaylist(this._data, config.show_forecast);
    this._steps = buildSteps(this._playlist.frames, {
      frameMs: config.frame_duration_ms,
      crossfadeMs: config.crossfade_ms,
    });
    const last = this._playlist.frames.length - 1;
    if (this._shown > last) this._shown = Math.max(0, last);
    if (this._playback.stepIndex > last) this._playback.moveTo(Math.max(0, last));
  }

  private _refresh(): Promise<void> {
    const shown = this._state === "ready" ? this._playlist.frames[this._shown]?.time : undefined;
    return this._load(shown ?? null, true);
  }

  /**
   * Fetch the frame list; `keepTime` keeps the position on that time. A `quiet` load
   * (the periodic refresh) never shows the loading state or stops playback.
   */
  private async _load(keepTime: string | null = null, quiet = false): Promise<void> {
    if (!this._hass || !this._config) return;
    const generation = ++this._generation;
    if (!quiet) {
      this._playback.pause();
      this._state = "loading";
      this.requestUpdate();
    }
    try {
      const data = await this._api.frames(this._period);
      if (generation !== this._generation) return;
      const fetchBlob = (url: string) => this._api.blob(url);
      const decode = (blob: Blob) => this.seams.createImageBitmap(blob);
      if (await this._basemap.load(data.basemap, fetchBlob, decode)) {
        this._compositor?.setBasemap(this._basemap.bitmap);
      }
      if (generation !== this._generation) return;
      await this._install(data, keepTime);
    } catch (error) {
      if (generation !== this._generation) return;
      console.warn("meteofrance-radar-card: frame list request failed", error);
      // A failed refresh keeps the frames already on screen; the next one retries.
      if (!quiet || !this._data) {
        this._state = "error";
        this.requestUpdate();
      }
    }
  }

  private async _install(data: FramesResponse, keepTime: string | null): Promise<void> {
    this._data = data;
    this._rebuild();
    this._compositor?.reset();
    const frames = this._playlist.frames;
    if (frames.length === 0) {
      this._playback.pause();
      this._state = "empty";
      this.requestUpdate();
      await this.updateComplete;
      this._compositor?.drawBasemap();
      return;
    }
    this._state = "ready";
    const autoplay = keepTime === null && (this._config?.autoplay ?? DEFAULTS.autoplay);
    const times = frames.map((frame) => frame.time);
    const kept = keepTime !== null ? findFrame(times, keepTime) : null;
    const index = restingIndex(this._playlist, kept, autoplay);
    this._shown = index;
    // A refresh during playback leaves the clock alone unless the frame moved.
    if (!this._playback.playing || index !== this._playback.stepIndex) this._playback.moveTo(index);
    this.requestUpdate();
    await this.updateComplete;
    if (this._playback.playing) return;
    await this._playback.seek(index).catch(logLayerError);
    if (autoplay) this._playback.play();
  }

  private _urls(): string[] {
    return this._playlist.frames.map((frame) => frame.url);
  }

  private _render(stepIndex: number, weight: number): boolean {
    const urls = stepUrls(this._steps, this._urls(), stepIndex);
    const compositor = this._compositor;
    if (!urls || !compositor) return false;
    this._loader.focus(this._urls(), stepIndex);
    const [urlA, urlB] = urls;
    const bitmapA = this._loader.bitmap(urlA);
    const bitmapB = urlB === null ? null : this._loader.bitmap(urlB);
    if (!bitmapA || (urlB !== null && !bitmapB)) return false;
    const layerB = urlB !== null && bitmapB ? { key: urlB, bitmap: bitmapB } : null;
    compositor.draw({ key: urlA, bitmap: bitmapA }, layerB, weight);
    const step = this._steps[stepIndex];
    const shown = step ? titleFrame(step, weight) : stepIndex;
    if (shown !== this._shown) {
      this._shown = shown;
      this.requestUpdate();
    }
    return true;
  }

  private _ensure(stepIndex: number): Promise<void> {
    const urls = stepUrls(this._steps, this._urls(), stepIndex);
    if (!urls) return Promise.resolve();
    this._loader.focus(this._urls(), stepIndex);
    this._shown = stepIndex;
    return this._loader.ensure(urls.filter((url): url is string => url !== null));
  }

  private _selectPeriod(period: PeriodName): void {
    if (period === this._period) return;
    this._period = period;
    void this._load();
  }
}

function logLayerError(error: unknown): void {
  console.warn("meteofrance-radar-card: layer failed", error);
}
