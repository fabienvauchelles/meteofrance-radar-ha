import { languageOf } from "./i18n";

const formatters = new Map<string, Intl.DateTimeFormat>();

function formatter(timeZone: string | undefined): Intl.DateTimeFormat {
  const key = timeZone ?? "";
  const cached = formatters.get(key);
  if (cached) return cached;
  const options: Intl.DateTimeFormatOptions = {
    hourCycle: "h23",
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  };
  let built: Intl.DateTimeFormat;
  try {
    built = new Intl.DateTimeFormat("en-GB", { ...options, timeZone });
  } catch {
    // An unknown zone name throws; the browser's own zone beats no title at all.
    built = new Intl.DateTimeFormat("en-GB", options);
  }
  formatters.set(key, built);
  return built;
}

/**
 * Format a slot time as `dd/mm/yy HH:MM` (English) or `dd/mm/yy HHhMM` (French),
 * in the Home Assistant time zone.
 */
export function formatSlot(iso: string, timeZone: string | undefined, language?: string): string {
  const parts: Record<string, string> = {};
  for (const part of formatter(timeZone).formatToParts(new Date(iso))) {
    parts[part.type] = part.value;
  }
  const separator = languageOf(language) === "fr" ? "h" : ":";
  return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}${separator}${parts.minute}`;
}
