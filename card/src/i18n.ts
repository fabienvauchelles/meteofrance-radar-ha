import type { PeriodName } from "./types";

export type Language = "en" | "fr";

export interface Strings {
  credit: string;
  gap(minutes: number): string;
  loading: string;
  empty: string;
  error: string;
  play: string;
  pause: string;
  stepBack: string;
  stepForward: string;
  timeSlider: string;
  periods: Record<PeriodName, string>;
  periodGroup: string;
  pin: string;
  noData: string;
  legend: string;
  attribution(radar: string, basemap: string): string;
  form: {
    default_period: string;
    autoplay: string;
    show_legend: string;
    frame_duration_ms: string;
    crossfade_ms: string;
    frameHelper: string;
    crossfadeHelper: string;
  };
}

const EN: Strings = {
  credit: "Météo-France data",
  gap: (minutes) => `gap of ${minutes} min skipped`,
  loading: "Loading the radar...",
  empty: "No radar image yet. The first one shows up a few minutes after setup.",
  error: "Could not load the radar images. Trying again in a minute.",
  play: "Play",
  pause: "Pause",
  stepBack: "Previous image",
  stepForward: "Next image",
  timeSlider: "Time",
  periods: { "3h": "3 h", "24h": "24 h", "7d": "7 d", "30d": "30 d", all: "All" },
  periodGroup: "Period",
  pin: "Home",
  noData: "no data",
  legend: "Rain rate",
  attribution: (radar, basemap) => `Radar: ${radar} | Basemap: ${basemap}`,
  form: {
    default_period: "Default period",
    autoplay: "Play on load",
    show_legend: "Show the legend",
    frame_duration_ms: "Time on each image (ms)",
    crossfade_ms: "Crossfade (ms)",
    frameHelper: "From 100 to 5000 ms.",
    crossfadeHelper: "From 0 to 2000 ms, never longer than the time on each image.",
  },
};

const FR: Strings = {
  credit: "Données Météo-France",
  gap: (minutes) => `saut de ${minutes} min`,
  loading: "Chargement du radar...",
  empty: "Pas encore d'image radar. La première arrive quelques minutes après l'installation.",
  error: "Impossible de charger les images radar. Nouvel essai dans une minute.",
  play: "Lecture",
  pause: "Pause",
  stepBack: "Image précédente",
  stepForward: "Image suivante",
  timeSlider: "Heure",
  periods: { "3h": "3 h", "24h": "24 h", "7d": "7 j", "30d": "30 j", all: "Tout" },
  periodGroup: "Période",
  pin: "Maison",
  noData: "pas de données",
  legend: "Intensité de pluie",
  attribution: (radar, basemap) => `Radar : ${radar} | Fond de carte : ${basemap}`,
  form: {
    default_period: "Période par défaut",
    autoplay: "Lecture automatique",
    show_legend: "Afficher la légende",
    frame_duration_ms: "Durée de chaque image (ms)",
    crossfade_ms: "Fondu enchaîné (ms)",
    frameHelper: "De 100 à 5000 ms.",
    crossfadeHelper: "De 0 à 2000 ms, jamais plus que la durée de chaque image.",
  },
};

/** Pick the language from a BCP 47 tag: French for any fr-*, English otherwise. */
export function languageOf(tag: string | undefined): Language {
  return tag?.toLowerCase().startsWith("fr") ? "fr" : "en";
}

export function stringsFor(tag: string | undefined): Strings {
  return languageOf(tag) === "fr" ? FR : EN;
}
