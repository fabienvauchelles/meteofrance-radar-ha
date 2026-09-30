import { vi } from "vitest";
import "../src/index";
import type { RainBarConfig } from "../src/rainbar/config";
import type { PinSegment, PinSeriesResponse } from "../src/rainbar/types";
import type { HomeAssistant } from "../src/types";

export const BAR_TAG = "meteofrance-rain-bar-card";
export const NOW = "2026-09-30T15:07:12Z";
export const WINDOW = { start: "2026-09-30T12:00:00Z", end: "2026-09-30T22:00:00Z" };
export const COLORS = Array.from(
  { length: 10 },
  (_, i) => `#0000${(i * 20 + 10).toString(16).padStart(2, "0")}`,
);

export type BarCard = HTMLElement & {
  setConfig(config: RainBarConfig): void;
  hass: HomeAssistant;
  getCardSize(): number;
  getGridOptions(): Record<string, unknown>;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

export function segment(
  source: PinSegment["source"],
  start: string,
  end: string,
  mmH: number | null,
  cls: number,
): PinSegment {
  return {
    source,
    start: `2026-09-30T${start}:00Z`,
    end: `2026-09-30T${end}:00Z`,
    mm_h: mmH,
    class: cls,
  };
}

/** A series on a 10-hour window: radar, then PIAF, AROME-PI and AROME. */
export function makeSeries(extra: Partial<PinSeriesResponse> = {}): PinSeriesResponse {
  return {
    version: "0.2.0",
    now: NOW,
    window: WINDOW,
    located: true,
    legend: {
      unit: "mm/h",
      levels: [0.1, 0.5, 1, 2, 4, 6, 10, 16, 25, 40, 70],
      colors: COLORS,
      nodata_color: "#808080",
    },
    segments: [
      segment("radar", "12:00", "12:05", 0, 0),
      segment("radar", "12:05", "12:10", null, 11),
      segment("radar", "15:00", "15:05", 0.43, 1),
      segment("piaf", "15:05", "15:10", 1.2, 3),
      segment("aromepi", "18:00", "18:15", 5, 5),
      segment("arome", "21:00", "22:00", 0.18, 1),
    ],
    sources: { radar: { status: "ok", latest: "2026-09-30T15:05:00Z" } },
    attribution: "Météo-France",
    ...extra,
  };
}

export interface FakeBarHass {
  hass: HomeAssistant;
  callApi: ReturnType<typeof vi.fn>;
  respond(next: () => PinSeriesResponse | Error): void;
}

export function makeBarHass(
  responder: () => PinSeriesResponse | Error = () => makeSeries(),
  language = "en",
  timeZone = "Europe/Paris",
): FakeBarHass {
  let current = responder;
  const callApi = vi.fn(async () => {
    const result = current();
    if (result instanceof Error) throw result;
    return result;
  });
  const hass = {
    callApi,
    fetchWithAuth: vi.fn(),
    locale: { language },
    language,
    config: { time_zone: timeZone },
  } as unknown as HomeAssistant;
  return { hass, callApi, respond: (next) => (current = next) };
}

export async function mountBar(
  config: Partial<RainBarConfig>,
  fake: FakeBarHass,
): Promise<BarCard> {
  const card = document.createElement(BAR_TAG) as BarCard;
  card.setConfig({ type: `custom:${BAR_TAG}`, ...config });
  card.hass = fake.hass;
  document.body.append(card);
  await settleBar(card);
  return card;
}

/** Let the fetch and the render run (works with real and fake timers). */
export async function settleBar(card: BarCard, ms = 0): Promise<void> {
  if (vi.isFakeTimers()) await vi.advanceTimersByTimeAsync(ms);
  for (let round = 0; round < 10; round += 1) await Promise.resolve();
  await card.updateComplete;
}

export function all(card: BarCard, selector: string): HTMLElement[] {
  return [...card.shadowRoot.querySelectorAll<HTMLElement>(selector)];
}

export function one(card: BarCard, selector: string): HTMLElement {
  const element = card.shadowRoot.querySelector<HTMLElement>(selector);
  if (!element) throw new Error(`no ${selector} in the card`);
  return element;
}

/** A percentage CSS property of an inline style, as a number. */
export function percent(element: HTMLElement, property: "left" | "width"): number {
  return Number.parseFloat(element.style[property]);
}
