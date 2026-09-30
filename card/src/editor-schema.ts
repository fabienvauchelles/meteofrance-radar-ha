// Schema and labels of the visual editor, rendered by Home Assistant's ha-form.

import { type CardConfig, DEFAULTS, LAYOUT_KEYS, type ResolvedConfig } from "./config";
import { stringsFor } from "./i18n";
import { PERIODS } from "./types";

export interface FormField {
  name: keyof ResolvedConfig;
  selector: Record<string, unknown>;
}

export interface EditorForm {
  schema: FormField[];
  computeLabel(field: { name: string }): string | undefined;
  computeHelper(field: { name: string }): string | undefined;
}

/** The form schema with labels in the given language. */
export function buildEditorForm(language: string | undefined): EditorForm {
  const strings = stringsFor(language);
  const form = strings.form;
  const schema: FormField[] = [
    {
      name: "default_period",
      selector: {
        select: {
          mode: "dropdown",
          options: PERIODS.map((value) => ({ value, label: strings.periods[value] })),
        },
      },
    },
    { name: "autoplay", selector: { boolean: {} } },
    { name: "show_legend", selector: { boolean: {} } },
    { name: "show_forecast", selector: { boolean: {} } },
    {
      name: "frame_duration_ms",
      selector: {
        number: { min: 100, max: 5000, step: 100, mode: "box", unit_of_measurement: "ms" },
      },
    },
    {
      name: "crossfade_ms",
      selector: { number: { min: 0, max: 2000, step: 50, mode: "box", unit_of_measurement: "ms" } },
    },
  ];
  const labels: Record<string, string> = {
    default_period: form.default_period,
    autoplay: form.autoplay,
    show_legend: form.show_legend,
    show_forecast: form.show_forecast,
    frame_duration_ms: form.frame_duration_ms,
    crossfade_ms: form.crossfade_ms,
  };
  const helpers: Record<string, string> = {
    frame_duration_ms: form.frameHelper,
    crossfade_ms: form.crossfadeHelper,
  };
  return {
    schema,
    computeLabel: (field) => labels[field.name],
    computeHelper: (field) => helpers[field.name],
  };
}

/** What the form shows: every option, with the default where the config leaves it out. */
export function formData(config: CardConfig): Record<string, unknown> {
  return { ...DEFAULTS, ...config };
}

/**
 * The config to save from the form values: the card type and layout keys of the
 * current config, then only the options that differ from their default.
 */
export function strippedConfig(current: CardConfig, values: Record<string, unknown>): CardConfig {
  const next: CardConfig = { type: current.type };
  for (const key of LAYOUT_KEYS) {
    if (key !== "type" && current[key] !== undefined) next[key] = current[key];
  }
  for (const key of Object.keys(DEFAULTS) as (keyof ResolvedConfig)[]) {
    const value = values[key];
    if (value !== undefined && value !== null && value !== "" && value !== DEFAULTS[key]) {
      (next as Record<string, unknown>)[key] = value;
    }
  }
  return next;
}

/** Language of the running frontend, for hooks that receive no hass object. */
export function frontendLanguage(): string | undefined {
  const root = document.querySelector("home-assistant") as
    | (Element & { hass?: { locale?: { language?: string }; language?: string } })
    | null;
  return root?.hass?.locale?.language ?? root?.hass?.language ?? navigator.language;
}

export function stubConfig(): Partial<CardConfig> {
  return { default_period: DEFAULTS.default_period, autoplay: DEFAULTS.autoplay };
}
