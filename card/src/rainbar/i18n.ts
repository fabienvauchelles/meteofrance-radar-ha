import { type Language, languageOf } from "../i18n";

export interface RainBarStrings {
  loading: string;
  error: string;
  notLocated: string;
  now: string;
  noData: string;
  bar: string;
  credit(attribution: string): string;
  form: { title: string; show_legend: string };
}

const EN: RainBarStrings = {
  loading: "Loading the rain forecast...",
  error: "Could not load the rain at home. Trying again in a few minutes.",
  notLocated: "Set your home location in the Home Assistant settings.",
  now: "Now",
  noData: "no data",
  bar: "Rain at home, past 3 hours and forecast",
  credit: (attribution) => `Source: ${attribution}`,
  form: { title: "Title", show_legend: "Show the legend" },
};

const FR: RainBarStrings = {
  loading: "Chargement de la prévision de pluie...",
  error: "Impossible de charger la pluie à la maison. Nouvel essai dans quelques minutes.",
  notLocated: "Indiquez l'emplacement de votre maison dans les paramètres de Home Assistant.",
  now: "Maintenant",
  noData: "pas de données",
  bar: "Pluie à la maison, 3 dernières heures et prévision",
  credit: (attribution) => `Source : ${attribution}`,
  form: { title: "Titre", show_legend: "Afficher la légende" },
};

export function rainBarStrings(language: Language): RainBarStrings {
  return language === "fr" ? FR : EN;
}

export { type Language, languageOf };
