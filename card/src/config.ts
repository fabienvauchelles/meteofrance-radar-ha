import { PERIODS, type PeriodName } from "./types";

export const CARD_TYPE = "custom:meteofrance-radar-card";

export const MIN_FRAME_MS = 100;
export const MAX_FRAME_MS = 5000;
export const MIN_CROSSFADE_MS = 0;
export const MAX_CROSSFADE_MS = 2000;

export interface CardConfig {
  type: string;
  default_period?: PeriodName;
  autoplay?: boolean;
  show_legend?: boolean;
  show_forecast?: boolean;
  frame_duration_ms?: number;
  crossfade_ms?: number;
  [layoutKey: string]: unknown;
}

export interface ResolvedConfig {
  default_period: PeriodName;
  autoplay: boolean;
  show_legend: boolean;
  show_forecast: boolean;
  frame_duration_ms: number;
  crossfade_ms: number;
}

export const DEFAULTS: ResolvedConfig = {
  default_period: "3h",
  autoplay: true,
  show_legend: true,
  show_forecast: true,
  frame_duration_ms: 500,
  crossfade_ms: 300,
};

// Keys Home Assistant itself may put on any card config (layout, visibility).
export const LAYOUT_KEYS = ["type", "grid_options", "layout_options", "view_layout", "visibility"];
const ALLOWED_KEYS = new Set([...LAYOUT_KEYS, ...Object.keys(DEFAULTS)]);

export class CardConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CardConfigError";
  }
}

function boolOption(
  config: CardConfig,
  key: "autoplay" | "show_legend" | "show_forecast",
): boolean {
  const value = config[key];
  if (value === undefined) return DEFAULTS[key];
  if (typeof value !== "boolean") throw new CardConfigError(`${key} must be true or false`);
  return value;
}

function numberOption(
  config: CardConfig,
  key: "frame_duration_ms" | "crossfade_ms",
  min: number,
  max: number,
): number {
  const value = config[key];
  if (value === undefined) return DEFAULTS[key];
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) {
    throw new CardConfigError(`${key} must be a number from ${min} to ${max}`);
  }
  return Math.round(value);
}

/**
 * Check a card config and fill in the defaults.
 * @throws CardConfigError on an unknown key or a value out of its range.
 */
export function validateConfig(config: CardConfig): ResolvedConfig {
  if (config === null || typeof config !== "object") {
    throw new CardConfigError("the card config must be an object");
  }
  for (const key of Object.keys(config)) {
    if (!ALLOWED_KEYS.has(key)) throw new CardConfigError(`unknown option: ${key}`);
  }
  const period = config.default_period ?? DEFAULTS.default_period;
  if (!PERIODS.includes(period)) {
    throw new CardConfigError(`default_period must be one of ${PERIODS.join(", ")}`);
  }
  const frame = numberOption(config, "frame_duration_ms", MIN_FRAME_MS, MAX_FRAME_MS);
  const crossfade = numberOption(config, "crossfade_ms", MIN_CROSSFADE_MS, MAX_CROSSFADE_MS);
  return {
    default_period: period,
    autoplay: boolOption(config, "autoplay"),
    show_legend: boolOption(config, "show_legend"),
    show_forecast: boolOption(config, "show_forecast"),
    frame_duration_ms: frame,
    // A fade longer than the time on a frame would never finish before the next one.
    crossfade_ms: Math.min(crossfade, frame),
  };
}
