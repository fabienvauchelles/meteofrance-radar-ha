// Shapes shared across the card: the frames API contract (docs/api.md, design section 7),
// the slice of the Home Assistant frontend object the card reads, and the seams tests inject.

export const PERIODS = ["3h", "24h", "7d", "30d", "all"] as const;
export type PeriodName = (typeof PERIODS)[number];

export interface RadarFrame {
  time: string;
  tier: string;
  gap_before_min: number;
  url: string;
}

export interface RadarGrid {
  width: number;
  height: number;
  center_lon: number;
  center_lat: number;
  zoom: number;
}

export interface RadarPin {
  x: number;
  y: number;
  inside: boolean;
}

export interface RadarLegend {
  unit: string;
  levels: number[];
  colors: string[];
  nodata_color: string;
}

export interface FramesResponse {
  version: string;
  style: string;
  grid: RadarGrid;
  basemap: string;
  pin: RadarPin | null;
  attribution: { radar: string; basemap: string };
  legend: RadarLegend;
  period: { name: PeriodName; from: string; to: string } | null;
  latest: string | null;
  oldest: string | null;
  frames: RadarFrame[];
  missing: number;
}

/** The part of the frontend `hass` object this card uses. */
export interface HomeAssistant {
  callApi<T>(method: "GET" | "POST", path: string): Promise<T>;
  fetchWithAuth(path: string, init?: RequestInit): Promise<Response>;
  locale?: { language?: string };
  language?: string;
  config: { time_zone?: string };
}

/**
 * Browser services the card reaches through one object, so tests replace canvas
 * contexts, bitmap decoding and the animation clock without touching globals.
 */
export interface CardSeams {
  createImageBitmap(blob: Blob): Promise<ImageBitmap>;
  context2d(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null;
  now(): number;
  requestFrame(callback: () => void): number;
  cancelFrame(handle: number): void;
}

export function browserSeams(): CardSeams {
  const hasRaf = typeof requestAnimationFrame === "function";
  return {
    createImageBitmap: (blob) => createImageBitmap(blob),
    context2d: (canvas) => canvas.getContext("2d"),
    now: () => performance.now(),
    requestFrame: (callback) =>
      hasRaf ? requestAnimationFrame(() => callback()) : window.setTimeout(callback, 16),
    cancelFrame: (handle) => (hasRaf ? cancelAnimationFrame(handle) : clearTimeout(handle)),
  };
}
