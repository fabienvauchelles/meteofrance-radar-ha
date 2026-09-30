// Pure layout of the rain bar: where a time falls on the bar, which hours get a label,
// and the text of each segment's tooltip. No DOM, so it is tested on its own.

import type { Language } from "../i18n";

const HOUR_MS = 3_600_000;
const QUARTER_MS = 900_000;
/** Label steps in hours, smallest first; the bar uses the first that fits. */
export const TICK_STEPS = [1, 2, 3, 6] as const;
export const MAX_LABELS = 8;
export const MAX_LABELS_NARROW = 4;
export const NARROW_WIDTH_PX = 360;

export interface Tick {
  time: number;
  percent: number;
  label: string;
}

/** Position of `time` on a bar from `start` to `end`, in percent, clamped to 0-100. */
export function percentOf(time: number, start: number, end: number): number {
  if (end <= start) return 0;
  return Math.min(100, Math.max(0, ((time - start) / (end - start)) * 100));
}

/** Left edge and width of the span [from, to] on the bar, both in percent. */
export function spanBox(
  from: number,
  to: number,
  start: number,
  end: number,
): { left: number; width: number } {
  const left = percentOf(from, start, end);
  return { left, width: Math.max(0, percentOf(to, start, end) - left) };
}

const formatters = new Map<string, Intl.DateTimeFormat>();

function clockFormatter(timeZone: string | undefined): Intl.DateTimeFormat {
  const key = timeZone ?? "";
  let formatter = formatters.get(key);
  if (!formatter) {
    const options: Intl.DateTimeFormatOptions = {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    };
    try {
      formatter = new Intl.DateTimeFormat("en-GB", { ...options, timeZone });
    } catch {
      // An unknown zone name falls back to the browser's own zone.
      formatter = new Intl.DateTimeFormat("en-GB", options);
    }
    formatters.set(key, formatter);
  }
  return formatter;
}

/** Local hour and minute of `time` in `timeZone`. */
export function localClock(time: number, timeZone: string | undefined): [number, number] {
  let hour = 0;
  let minute = 0;
  for (const part of clockFormatter(timeZone).formatToParts(new Date(time))) {
    if (part.type === "hour") hour = Number(part.value) % 24;
    if (part.type === "minute") minute = Number(part.value);
  }
  return [hour, minute];
}

/** Clock time: en "15:05", fr "15h05". */
export function formatClock(
  time: number,
  timeZone: string | undefined,
  language: Language,
): string {
  const [hour, minute] = localClock(time, timeZone);
  const hh = String(hour).padStart(2, "0");
  const mm = String(minute).padStart(2, "0");
  return language === "fr" ? `${hh}h${mm}` : `${hh}:${mm}`;
}

/** Hour label under the bar: en "15:00", fr "15h". */
export function formatHour(hour: number, language: Language): string {
  const hh = String(hour).padStart(2, "0");
  return language === "fr" ? `${hh}h` : `${hh}:00`;
}

/** Rain rate with at most 2 decimals: en "1.2 mm/h", fr "1,2 mm/h". */
export function formatRate(mmH: number, language: Language): string {
  const text = String(Math.round(mmH * 100) / 100);
  return `${language === "fr" ? text.replace(".", ",") : text} mm/h`;
}

/** Tooltip of a segment: "15:05-15:10 · 1.2 mm/h", or the no-data text. */
export function segmentTooltip(
  from: number,
  to: number,
  mmH: number | null,
  timeZone: string | undefined,
  language: Language,
  noData: string,
): string {
  const range = `${formatClock(from, timeZone, language)}-${formatClock(to, timeZone, language)}`;
  return `${range} · ${mmH === null ? noData : formatRate(mmH, language)}`;
}

/** Full local hours inside [start, end], as [time, local hour] pairs. */
function localHours(start: number, end: number, timeZone: string | undefined): [number, number][] {
  const hours: [number, number][] = [];
  // Quarter steps catch zones whose offset is not a whole hour.
  for (let time = Math.ceil(start / QUARTER_MS) * QUARTER_MS; time <= end; time += QUARTER_MS) {
    const [hour, minute] = localClock(time, timeZone);
    if (minute === 0) hours.push([time, hour]);
  }
  return hours;
}

/** Smallest step of TICK_STEPS that labels at most `maxLabels` of the local `hours`. */
export function tickStep(hours: readonly number[], maxLabels: number): number {
  for (const step of TICK_STEPS) {
    if (hours.filter((hour) => hour % step === 0).length <= maxLabels) return step;
  }
  return TICK_STEPS[TICK_STEPS.length - 1] ?? 6;
}

/** Hour labels for the bar in `timeZone`, at most `maxLabels` unless even 6 h is too dense. */
export function hourTicks(
  start: number,
  end: number,
  timeZone: string | undefined,
  language: Language,
  maxLabels = MAX_LABELS,
): Tick[] {
  if (end - start < HOUR_MS / 4) return [];
  const hours = localHours(start, end, timeZone);
  const step = tickStep(
    hours.map(([, hour]) => hour),
    maxLabels,
  );
  return hours
    .filter(([, hour]) => hour % step === 0)
    .map(([time, hour]) => ({
      time,
      percent: percentOf(time, start, end),
      label: formatHour(hour, language),
    }));
}

/** Label budget for a card of `widthPx` (0 when unknown). */
export function maxLabelsFor(widthPx: number): number {
  return widthPx > 0 && widthPx < NARROW_WIDTH_PX ? MAX_LABELS_NARROW : MAX_LABELS;
}
