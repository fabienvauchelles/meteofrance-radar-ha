// Visual editor element. HA's plain form (getConfigForm) hands ha-form the raw config,
// so an unset option showed as empty or off; this element feeds ha-form the effective
// values and saves only what differs from the defaults.

import { html, LitElement, type TemplateResult } from "lit";
import type { CardConfig } from "./config";
import { buildEditorForm, formData, frontendLanguage, strippedConfig } from "./editor-schema";
import type { HomeAssistant } from "./types";

export { frontendLanguage, stubConfig } from "./editor-schema";

export const EDITOR_TAG = "meteofrance-radar-card-editor";

export class MeteoFranceRadarCardEditor extends LitElement {
  private _hass?: HomeAssistant;
  private _config?: CardConfig;

  set hass(hass: HomeAssistant) {
    const before = this._hass?.locale?.language ?? this._hass?.language;
    this._hass = hass;
    if (before !== (hass.locale?.language ?? hass.language)) this.requestUpdate();
  }

  get hass(): HomeAssistant | undefined {
    return this._hass;
  }

  setConfig(config: CardConfig): void {
    this._config = config;
    this.requestUpdate();
  }

  render(): TemplateResult {
    const config = this._config;
    if (!config) return html``;
    const language = this._hass?.locale?.language ?? this._hass?.language ?? frontendLanguage();
    const form = buildEditorForm(language);
    return html`
      <ha-form
        .hass=${this._hass}
        .data=${formData(config)}
        .schema=${form.schema}
        .computeLabel=${form.computeLabel}
        .computeHelper=${form.computeHelper}
        @value-changed=${(event: CustomEvent<{ value: Record<string, unknown> }>) =>
          this._changed(event)}
      ></ha-form>
    `;
  }

  private _changed(event: CustomEvent<{ value: Record<string, unknown> }>): void {
    event.stopPropagation();
    if (!this._config) return;
    const config = strippedConfig(this._config, event.detail.value);
    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }),
    );
  }
}

if (!customElements.get(EDITOR_TAG)) customElements.define(EDITOR_TAG, MeteoFranceRadarCardEditor);
