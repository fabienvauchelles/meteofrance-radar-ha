import { MeteoFranceRainBarCard } from "./card";
import { RAIN_BAR_TAG } from "./config";

export const DOCUMENTATION_URL = "https://github.com/fabienvauchelles/meteofrance-radar-ha";

export interface CustomCardEntry {
  type: string;
  name: string;
  description: string;
  preview?: boolean;
  documentationURL?: string;
}

/** Add an entry to the dashboard card picker once, whatever the number of bundle loads. */
export function addCustomCard(entry: CustomCardEntry): void {
  const win = window as unknown as { customCards?: CustomCardEntry[] };
  win.customCards = win.customCards ?? [];
  if (!win.customCards.some((existing) => existing.type === entry.type)) {
    win.customCards.push(entry);
  }
}

/** Define `meteofrance-rain-bar-card` and list it in the card picker. */
export function registerRainBarCard(): void {
  if (!customElements.get(RAIN_BAR_TAG)) {
    customElements.define(RAIN_BAR_TAG, MeteoFranceRainBarCard);
  }
  addCustomCard({
    type: RAIN_BAR_TAG,
    name: "Météo-France Rain Bar",
    description: "Rain at your home: the past 3 hours from the radar, then the forecast.",
    preview: true,
    documentationURL: DOCUMENTATION_URL,
  });
}
