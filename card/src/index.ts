import { MeteoFranceRadarCard } from "./card";

export const CARD_TAG = "meteofrance-radar-card";

if (!customElements.get(CARD_TAG)) customElements.define(CARD_TAG, MeteoFranceRadarCard);

interface CustomCardEntry {
  type: string;
  name: string;
  description: string;
  preview?: boolean;
  documentationURL?: string;
}

const win = window as unknown as { customCards?: CustomCardEntry[] };
win.customCards = win.customCards ?? [];
if (!win.customCards.some((entry) => entry.type === CARD_TAG)) {
  win.customCards.push({
    type: CARD_TAG,
    name: "Météo-France Radar",
    description: "Plays the Météo-France rain radar over France, with a pin at your home.",
    preview: true,
    documentationURL: "https://github.com/fabienvauchelles/meteofrance-radar-ha",
  });
}
