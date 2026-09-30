import { html, LitElement, type TemplateResult } from "lit";
import { createRef } from "lit/directives/ref.js";
import { RadarApi } from "./api";
import { Compositor } from "./compositor";
import { type CardConfig, DEFAULTS, type ResolvedConfig, validateConfig } from "./config";
import { buildConfigForm, type ConfigForm, frontendLanguage, stubConfig } from "./editor";
import { formatSlot } from "./format";
import { languageOf, stringsFor } from "./i18n";
import { LayerLoader } from "./loader";
import { Playback } from "./playback";
import { cardStyles } from "./styles";
import { buildSteps, findFrame, type Step, stepUrls, titleFrame } from "./timeline";
import {
  browserSeams,
  type CardSeams,
  type FramesResponse,
  type HomeAssistant,
  type PeriodName,
} from "./types";
import { type LoadState, pinPosition, renderCard, type ViewModel } from "./view";

export const REFRESH_MS = 60_000;
const DEFAULT_WIDTH = 1920;
const DEFAULT_HEIGHT = 1080;

export class MeteoFranceRadarCard extends LitElement {
  static styles = cardStyles;

  /** Browser services; tests replace them before the card is connected. */
  seams: CardSeams = browserSeams();

  private _config?: ResolvedConfig;
  private _hass?: HomeAssistant;
  private _period: PeriodName = DEFAULTS.default_period;
  private _data: FramesResponse | null = null;
  private _state: LoadState = "loading";
  private _steps: Step[] = [];
  private _shown = 0;
  private _generation = 0;
  private _refreshTimer: number | null = null;
  private _resumeOnConnect = false;
  private _basemapUrl: string | null = null;
  private _basemap: ImageBitmap | null = null;
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

  static getConfigForm(): ConfigForm {
    return buildConfigForm(frontendLanguage());
  }

  static getStubConfig(): Partial<CardConfig> {
    return stubConfig();
  }

  setConfig(config: CardConfig): void {
    const resolved = validateConfig(config);
    const periodChanged = this._config?.default_period !== resolved.default_period;
    this._config = resolved;
    this._steps = this._buildSteps();
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
    const language = (h?: HomeAssistant) => h?.locale?.language ?? h?.language;
    if (
      language(previous) !== language(hass) ||
      previous?.config.time_zone !== hass.config.time_zone
    ) {
      this.requestUpdate();
    }
  }

  get hass(): HomeAssistant | undefined {
    return this._hass;
  }

  getCardSize(): number {
    return 7;
  }

  getGridOptions(): { columns: number; rows: "auto"; min_columns: number } {
    return { columns: 12, rows: "auto", min_columns: 6 };
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
    if (!this._compositor?.matches(canvas, width, height)) {
      this._compositor = new Compositor(canvas, width, height, this.seams.context2d);
      this._compositor.setBasemap(this._basemap);
      this._compositor.drawBasemap();
    }
  }

  render(): TemplateResult {
    if (!this._config) return html``;
    const language = languageOf(this._hass?.locale?.language ?? this._hass?.language);
    const data = this._data;
    const frame = this._state === "ready" ? data?.frames[this._shown] : undefined;
    const vm: ViewModel = {
      strings: stringsFor(language),
      language,
      state: this._state,
      time: frame ? formatSlot(frame.time, this._hass?.config.time_zone, language) : null,
      gapMin: frame?.gap_before_min ?? 0,
      playing: this._playback.playing,
      waiting: this._playback.waiting,
      position: this._playback.stepIndex,
      count: this._state === "ready" ? this._steps.length : 0,
      period: this._period,
      pin: pinPosition(data),
      aspect: (data?.grid.width ?? DEFAULT_WIDTH) / (data?.grid.height ?? DEFAULT_HEIGHT),
      legend: this._config.show_legend ? (data?.legend ?? null) : null,
      attribution: data?.attribution ?? null,
    };
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

  private _buildSteps(): Step[] {
    const config = this._config ?? DEFAULTS;
    return buildSteps(this._data?.frames ?? [], {
      frameMs: config.frame_duration_ms,
      crossfadeMs: config.crossfade_ms,
    });
  }

  private _refresh(): Promise<void> {
    const shown = this._state === "ready" ? this._data?.frames[this._shown]?.time : undefined;
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
      await this._loadBasemap(data.basemap);
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

  private async _loadBasemap(url: string): Promise<void> {
    if (url === this._basemapUrl) return;
    try {
      const bitmap = await this.seams.createImageBitmap(await this._api.blob(url));
      this._basemap?.close();
      this._basemap = bitmap;
      this._basemapUrl = url;
      this._compositor?.setBasemap(bitmap);
    } catch (error) {
      // Rain over a blank background still beats no radar at all.
      console.warn("meteofrance-radar-card: basemap failed", error);
    }
  }

  private async _install(data: FramesResponse, keepTime: string | null): Promise<void> {
    this._data = data;
    this._steps = this._buildSteps();
    this._compositor?.reset();
    const frames = data.frames;
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
    const index = keepTime !== null ? findFrame(times, keepTime) : autoplay ? 0 : frames.length - 1;
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
    return (this._data?.frames ?? []).map((frame) => frame.url);
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
