// Visual editor through Home Assistant's built-in form (getConfigForm). Both options
// default to empty or false, which the form shows correctly for an absent key.

import { type RainBarConfig, validateRainBarConfig } from "./config";
import { languageOf, rainBarStrings } from "./i18n";

export interface RainBarFormField {
  name: "title" | "show_legend";
  selector: Record<string, unknown>;
}

export interface RainBarConfigForm {
  schema: RainBarFormField[];
  computeLabel(field: { name: string }): string | undefined;
  assertConfig(config: RainBarConfig): void;
}

/** The form schema with labels in the language of the given BCP 47 tag. */
export function buildRainBarForm(language: string | undefined): RainBarConfigForm {
  const labels: Record<string, string> = rainBarStrings(languageOf(language)).form;
  return {
    schema: [
      { name: "title", selector: { text: {} } },
      { name: "show_legend", selector: { boolean: {} } },
    ],
    computeLabel: (field) => labels[field.name],
    // Throwing switches the dashboard to the YAML editor, which shows the message.
    assertConfig: (config) => {
      validateRainBarConfig(config);
    },
  };
}
