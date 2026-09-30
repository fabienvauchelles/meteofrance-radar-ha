// What the dashboard calls on the radar card besides its config and hass: the editor,
// the stub config, the sizing hints, and the panel view flag.

import { LitElement } from "lit";
import { GRID_OPTIONS, type GridOptions } from "./card-data";
import type { CardConfig } from "./config";
import { EDITOR_TAG, stubConfig } from "./editor";
import { ensureHaForm } from "./ha-form-loader";
import { cardStyles } from "./styles";

export class RadarCardHost extends LitElement {
  static styles = cardStyles;

  /** The card is alone in a panel view, so it must fit under the header. */
  protected panel = false;

  static async getConfigElement(): Promise<HTMLElement> {
    await ensureHaForm();
    return document.createElement(EDITOR_TAG);
  }

  static getStubConfig(): Partial<CardConfig> {
    return stubConfig();
  }

  /** Set by hui-card: "panel" in a panel view, other values elsewhere. */
  set layout(value: string | undefined) {
    this._setPanel(value === "panel");
  }

  /** The older flag hui-card still sets next to `layout`. */
  set isPanel(value: boolean) {
    this._setPanel(value);
  }

  getCardSize(): number {
    return 7;
  }

  getGridOptions(): GridOptions {
    return { ...GRID_OPTIONS };
  }

  private _setPanel(panel: boolean): void {
    if (panel === this.panel) return;
    this.panel = panel;
    // Reflected so the host drops the height it would otherwise stretch to.
    this.toggleAttribute("panel", panel);
    this.requestUpdate();
  }
}
