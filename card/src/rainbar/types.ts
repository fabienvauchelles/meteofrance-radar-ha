// Contract of GET /api/meteofrance_radar/pin_series.

import type { RadarLegend } from "../types";

export type SegmentSource = "radar" | "piaf" | "aromepi" | "arome";

/** Rain rate over [start, end] at the home pin. `class` is the palette index: 0 dry, 1-10, 11 no data. */
export interface PinSegment {
  source: SegmentSource;
  start: string;
  end: string;
  mm_h: number | null;
  class: number;
}

export interface SourceStatus {
  status: string;
  latest?: string | null;
  run?: string | null;
}

export interface PinSeriesResponse {
  version: string;
  now: string;
  window: { start: string; end: string };
  located: boolean;
  legend: RadarLegend;
  segments: PinSegment[];
  sources: Partial<Record<SegmentSource, SourceStatus>>;
  attribution: string;
}
