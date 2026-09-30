export const RAIN_BAR_TAG = "meteofrance-rain-bar-card";
export const RAIN_BAR_TYPE = `custom:${RAIN_BAR_TAG}`;

export interface RainBarConfig {
  type: string;
  title?: string;
  show_legend?: boolean;
  [layoutKey: string]: unknown;
}

export interface ResolvedRainBarConfig {
  title: string | null;
  show_legend: boolean;
}

export const RAIN_BAR_DEFAULTS: ResolvedRainBarConfig = { title: null, show_legend: false };

// Keys Home Assistant itself may put on any card config (layout, visibility).
const LAYOUT_KEYS = ["type", "grid_options", "layout_options", "view_layout", "visibility"];
const ALLOWED_KEYS = new Set([...LAYOUT_KEYS, "title", "show_legend"]);

export class RainBarConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RainBarConfigError";
  }
}

/**
 * Check a rain bar config and fill in the defaults.
 * @throws RainBarConfigError on an unknown key or a value of the wrong type.
 */
export function validateRainBarConfig(config: RainBarConfig): ResolvedRainBarConfig {
  if (config === null || typeof config !== "object") {
    throw new RainBarConfigError("the card config must be an object");
  }
  for (const key of Object.keys(config)) {
    if (!ALLOWED_KEYS.has(key)) throw new RainBarConfigError(`unknown option: ${key}`);
  }
  const { title, show_legend: showLegend } = config;
  if (title !== undefined && typeof title !== "string") {
    throw new RainBarConfigError("title must be text");
  }
  if (showLegend !== undefined && typeof showLegend !== "boolean") {
    throw new RainBarConfigError("show_legend must be true or false");
  }
  return {
    title: title?.trim() ? title : RAIN_BAR_DEFAULTS.title,
    show_legend: showLegend ?? RAIN_BAR_DEFAULTS.show_legend,
  };
}
