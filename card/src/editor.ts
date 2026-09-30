// Visual editor through Home Assistant's built-in form (getConfigForm): no editor
// element to ship, the frontend renders the selectors below.

import { type CardConfig, DEFAULTS, validateConfig } from "./config";
import { stringsFor } from "./i18n";
import { PERIODS } from "./types";

export interface FormField {
  name: keyof typeof DEFAULTS;
  selector: Record<string, unknown>;
  /** Shown by the form when the key is absent, so it matches what the card does. */
  default?: unknown;
}

export interface ConfigForm {
  schema: FormField[];
  computeLabel(field: { name: string }): string | undefined;
  computeHelper(field: { name: string }): string | undefined;
  assertConfig(config: CardConfig): void;
}

/** The form schema with labels in the given language. */
export function buildConfigForm(language: string | undefined): ConfigForm {
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
  for (const field of schema) field.default = DEFAULTS[field.name];
  const labels: Record<string, string> = {
    default_period: form.default_period,
    autoplay: form.autoplay,
    show_legend: form.show_legend,
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
    // Throwing switches the dashboard to the YAML editor, which shows the message.
    assertConfig: (config) => {
      validateConfig(config);
    },
  };
}

/** Language of the running frontend; the static form hook receives no hass object. */
export function frontendLanguage(): string | undefined {
  const root = document.querySelector("home-assistant") as
    | (Element & { hass?: { locale?: { language?: string }; language?: string } })
    | null;
  return root?.hass?.locale?.language ?? root?.hass?.language ?? navigator.language;
}

export function stubConfig(): Partial<CardConfig> {
  return { default_period: DEFAULTS.default_period, autoplay: DEFAULTS.autoplay };
}
