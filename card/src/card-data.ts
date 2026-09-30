// What the radar card derives from its state: the view model handed to the templates,
// the dashboard sizing, and the basemap bitmap it keeps across frame list refreshes.

import type { CardConfig, ResolvedConfig } from "./config";
import { formatSlot } from "./format";
import { languageOf, stringsFor } from "./i18n";
import { nowPercent, type Playlist } from "./playlist";
import type { FramesResponse, HomeAssistant, PeriodName } from "./types";
import { type LoadState, pinPosition, type ViewModel } from "./view";

export const DEFAULT_WIDTH = 1920;
export const DEFAULT_HEIGHT = 1080;

export interface GridOptions {
  columns: number;
  rows: "auto";
  min_columns: number;
  min_rows: number;
}

/** Sizing for the sections view: full width by default, down to half a section. */
export const GRID_OPTIONS: GridOptions = { columns: 12, rows: "auto", min_columns: 6, min_rows: 4 };

/** Whether the dashboard gives the card a fixed number of rows to fill. */
export function wantsFill(config: CardConfig): boolean {
  const grid = config.grid_options as { rows?: unknown } | undefined;
  return typeof grid?.rows === "number";
}

/** The user's frontend language: the profile locale first, then the older field. */
export function languageTag(hass: HomeAssistant | undefined): string | undefined {
  return hass?.locale?.language ?? hass?.language;
}

export interface ViewInput {
  config: ResolvedConfig;
  hass: HomeAssistant | undefined;
  data: FramesResponse | null;
  playlist: Playlist;
  state: LoadState;
  shown: number;
  playing: boolean;
  waiting: boolean;
  position: number;
  stepCount: number;
  period: PeriodName;
  fill: boolean;
  panel: boolean;
}

export function buildViewModel(input: ViewInput): ViewModel {
  const { data, hass } = input;
  const language = languageOf(languageTag(hass));
  const ready = input.state === "ready";
  const frame = ready ? input.playlist.frames[input.shown] : undefined;
  return {
    strings: stringsFor(language),
    language,
    state: input.state,
    time: frame ? formatSlot(frame.time, hass?.config.time_zone, language) : null,
    gapMin: frame?.gap_before_min ?? 0,
    leadMin: frame?.forecast ? (frame.lead_min ?? 0) : null,
    nowPct: ready ? nowPercent(input.playlist) : null,
    // A panel view bounds the card by the viewport, which replaces the grid rows.
    fill: input.fill && !input.panel,
    panel: input.panel,
    playing: input.playing,
    waiting: input.waiting,
    position: input.position,
    count: ready ? input.stepCount : 0,
    period: input.period,
    pin: pinPosition(data),
    aspect: (data?.grid.width ?? DEFAULT_WIDTH) / (data?.grid.height ?? DEFAULT_HEIGHT),
    legend: input.config.show_legend ? (data?.legend ?? null) : null,
    attribution: data?.attribution ?? null,
  };
}

/** The decoded basemap, fetched again only when its URL changes. */
export class BasemapSource {
  private url: string | null = null;
  bitmap: ImageBitmap | null = null;

  /**
   * Load the basemap at `url`; true when a new bitmap replaced the old one. A failure
   * keeps the previous one: rain over a blank background still beats no radar at all.
   */
  async load(
    url: string,
    fetchBlob: (url: string) => Promise<Blob>,
    decode: (blob: Blob) => Promise<ImageBitmap>,
  ): Promise<boolean> {
    if (url === this.url) return false;
    try {
      const bitmap = await decode(await fetchBlob(url));
      this.bitmap?.close();
      this.bitmap = bitmap;
      this.url = url;
      return true;
    } catch (error) {
      console.warn("meteofrance-radar-card: basemap failed", error);
      return false;
    }
  }
}
