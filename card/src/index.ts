import { MeteoFranceRadarCard } from "./card";
import { addCustomCard, DOCUMENTATION_URL, registerRainBarCard } from "./rainbar/register";

export const CARD_TAG = "meteofrance-radar-card";
export { RAIN_BAR_TAG } from "./rainbar/config";

if (!customElements.get(CARD_TAG)) customElements.define(CARD_TAG, MeteoFranceRadarCard);

addCustomCard({
  type: CARD_TAG,
  name: "Météo-France Radar",
  description: "Plays the Météo-France rain radar over France, with a pin at your home.",
  preview: true,
  documentationURL: DOCUMENTATION_URL,
});

registerRainBarCard();
