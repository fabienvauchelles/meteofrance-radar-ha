import { LitElement, type TemplateResult } from "lit";
import { frontendLanguage } from "../editor";
import type { HomeAssistant } from "../types";
import { fetchPinSeries } from "./api";
import {
  RAIN_BAR_DEFAULTS,
  type RainBarConfig,
  type ResolvedRainBarConfig,
  validateRainBarConfig,
} from "./config";
import { buildRainBarForm, type RainBarConfigForm } from "./form";
import { maxLabelsFor } from "./geometry";
import { languageOf, rainBarStrings } from "./i18n";
import { rainBarStyles } from "./styles";
import type { PinSeriesResponse } from "./types";
import { type BarState, renderRainBar } from "./view";

export const RAIN_BAR_REFRESH_MS = 300_000;
export const NOW_TICK_MS = 60_000;

/** One horizontal bar of the rain rate at the home pin: past 3 hours and the forecast. */
export class MeteoFranceRainBarCard extends LitElement {
  static styles = rainBarStyles;

  private _config: ResolvedRainBarConfig = RAIN_BAR_DEFAULTS;
  private _hass?: HomeAssistant;
  private _data: PinSeriesResponse | null = null;
  private _state: BarState = "loading";
  private _now = Date.now();
  private _width = 0;
  private _refreshTimer: number | null = null;
  private _nowTimer: number | null = null;
  private _resizeObserver: ResizeObserver | null = null;
  private _generation = 0;

  static getConfigForm(): RainBarConfigForm {
    return buildRainBarForm(frontendLanguage());
  }

  static getStubConfig(): Partial<RainBarConfig> {
    return {};
  }

  setConfig(config: RainBarConfig): void {
    this._config = validateRainBarConfig(config);
    this.requestUpdate();
  }

  set hass(hass: HomeAssistant) {
    const first = this._hass === undefined;
    this._hass = hass;
    // The frontend sets hass on every state change; only the first one triggers a fetch.
    if (first && this.isConnected) void this._load();
    this.requestUpdate();
  }

  get hass(): HomeAssistant | undefined {
    return this._hass;
  }

  getCardSize(): number {
    return 2;
  }

  getGridOptions(): { columns: number; rows: "auto"; min_columns: number; min_rows: number } {
    return { columns: 12, rows: "auto", min_columns: 3, min_rows: 1 };
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._now = Date.now();
    this._refreshTimer = window.setInterval(() => void this._load(), RAIN_BAR_REFRESH_MS);
    this._nowTimer = window.setInterval(() => {
      this._now = Date.now();
      this.requestUpdate();
    }, NOW_TICK_MS);
    if (typeof ResizeObserver === "function") {
      this._resizeObserver = new ResizeObserver((entries) => {
        const width = entries[0]?.contentRect.width ?? 0;
        if (width !== this._width) {
          this._width = width;
          this.requestUpdate();
        }
      });
      this._resizeObserver.observe(this);
    }
    if (this._hass) void this._load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._refreshTimer !== null) window.clearInterval(this._refreshTimer);
    if (this._nowTimer !== null) window.clearInterval(this._nowTimer);
    this._refreshTimer = null;
    this._nowTimer = null;
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    // A response landing after removal is ignored.
    this._generation += 1;
  }

  private async _load(): Promise<void> {
    const hass = this._hass;
    if (!hass) return;
    const generation = ++this._generation;
    try {
      const data = await fetchPinSeries(hass);
      if (generation !== this._generation) return;
      this._data = data;
      this._state = "ready";
    } catch (error) {
      if (generation !== this._generation) return;
      console.warn("meteofrance-rain-bar-card: pin series failed", error);
      // Keep the last good bar; the next refresh tries again.
      this._state = "error";
    }
    this._now = Date.now();
    this.requestUpdate();
  }

  protected render(): TemplateResult {
    const language = languageOf(this._hass?.locale?.language ?? this._hass?.language);
    return renderRainBar({
      strings: rainBarStrings(language),
      language,
      title: this._config.title,
      showLegend: this._config.show_legend,
      state: this._state,
      data: this._data,
      now: this._now,
      timeZone: this._hass?.config?.time_zone,
      maxLabels: maxLabelsFor(this._width),
    });
  }
}
