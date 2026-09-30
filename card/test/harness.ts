import { vi } from "vitest";
import "../src/index";
import type { CardConfig } from "../src/config";
import type {
  CardSeams,
  ForecastInfo,
  FramesResponse,
  HomeAssistant,
  PeriodName,
  RadarFrame,
} from "../src/types";

export const STYLE = "3fa1c09b2e";
export const TAG = "meteofrance-radar-card";

export type Card = HTMLElement & {
  setConfig(config: CardConfig): void;
  hass: HomeAssistant;
  seams: CardSeams;
  getCardSize(): number;
  getGridOptions(): Record<string, unknown>;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

/** Frames every 5 minutes ending at `latest`; `gaps` maps a frame index to its gap. */
export function makeFrames(
  count: number,
  latest = "2026-09-30T10:30:00Z",
  gaps: Record<number, number> = {},
): RadarFrame[] {
  const end = Date.parse(latest);
  return Array.from({ length: count }, (_, index) => {
    const time = new Date(end - (count - 1 - index) * 300_000);
    const slot = time.toISOString().slice(0, 16).replace(/[-:]/g, "");
    return {
      time: time.toISOString().replace(".000Z", "Z"),
      tier: "5min",
      gap_before_min: gaps[index] ?? 0,
      url: `/api/meteofrance_radar/layers/${STYLE}/${slot}Z.png`,
    };
  });
}

/** A PIAF run whose frames come `leads` minutes after `now`. */
export function makeForecast(
  leads: number[],
  now = "2026-09-30T10:30:00Z",
  run = "2026-09-30T10:15:00Z",
): ForecastInfo {
  const base = Date.parse(now);
  const runSlot = run.slice(0, 16).replace(/[-:]/g, "");
  return {
    status: "ok",
    source: "piaf",
    run,
    now,
    frames: leads.map((lead) => {
      const time = new Date(base + lead * 60_000);
      const slot = time.toISOString().slice(0, 16).replace(/[-:]/g, "");
      return {
        time: time.toISOString().replace(".000Z", "Z"),
        lead_min: lead,
        url: `/api/meteofrance_radar/forecast/${STYLE}/${runSlot}Z/${slot}Z.png`,
      };
    }),
  };
}

export function makeResponse(
  frames: RadarFrame[],
  extra: Partial<FramesResponse> = {},
): FramesResponse {
  return {
    version: "0.1.0",
    style: STYLE,
    grid: { width: 1920, height: 1080, center_lon: 2.5, center_lat: 46.6, zoom: 6.4 },
    basemap: "/meteofrance_radar/basemap.png?v=0.1.0",
    pin: { x: 960, y: 270, inside: true },
    attribution: { radar: "Météo-France", basemap: "IGN ADMIN EXPRESS 2018, Natural Earth" },
    legend: {
      unit: "mm/h",
      levels: [0.1, 0.5, 1, 2, 4, 6, 10, 16, 25, 40, 70],
      colors: Array.from(
        { length: 10 },
        (_, i) => `#0000${(i * 20).toString(16).padStart(2, "0")}`,
      ),
      nodata_color: "#808080",
    },
    period: frames.length
      ? { name: "3h", from: frames[0]?.time ?? "", to: frames[frames.length - 1]?.time ?? "" }
      : null,
    latest: frames[frames.length - 1]?.time ?? null,
    oldest: frames[0]?.time ?? null,
    frames,
    missing: 0,
    ...extra,
  };
}

type Responder = (period: PeriodName) => FramesResponse | Error;

export interface FakeHass {
  hass: HomeAssistant;
  callApi: ReturnType<typeof vi.fn>;
  fetchWithAuth: ReturnType<typeof vi.fn>;
  periods: PeriodName[];
  respond(responder: Responder): void;
}

export function makeHass(
  responder: Responder,
  language = "en",
  timeZone = "Europe/Paris",
): FakeHass {
  let current = responder;
  const periods: PeriodName[] = [];
  const callApi = vi.fn(async (_method: string, path: string) => {
    const period = (new URL(path, "http://ha").searchParams.get("period") ?? "3h") as PeriodName;
    periods.push(period);
    const result = current(period);
    if (result instanceof Error) throw result;
    return result;
  });
  const fetchWithAuth = vi.fn(async (url: string) => ({
    ok: true,
    status: 200,
    blob: async () => new Blob([url], { type: "image/png" }),
  }));
  const hass = {
    callApi,
    fetchWithAuth,
    locale: { language },
    language,
    config: { time_zone: timeZone },
  } as unknown as HomeAssistant;
  return { hass, callApi, fetchWithAuth, periods, respond: (next) => (current = next) };
}

export interface FakeSeams {
  seams: CardSeams;
  /** URL of the last layer bitmap drawn onto a composite. */
  lastLayer(): string | null;
}

/** Canvas contexts that record draws, bitmaps that remember their URL, a setTimeout clock. */
export function makeSeams(): FakeSeams {
  let last: string | null = null;
  const context = {
    globalAlpha: 1,
    clearRect: vi.fn(),
    drawImage: vi.fn((image: unknown) => {
      const url = (image as { url?: string }).url;
      if (url?.includes("/layers/") || url?.includes("/forecast/")) last = url;
    }),
  } as unknown as CanvasRenderingContext2D;
  const seams: CardSeams = {
    createImageBitmap: async (blob) =>
      ({
        url: await blob.text(),
        width: 1920,
        height: 1080,
        close: vi.fn(),
      }) as unknown as ImageBitmap,
    context2d: () => context,
    now: () => Date.now(),
    requestFrame: (callback) => setTimeout(callback, 16) as unknown as number,
    cancelFrame: (handle) => clearTimeout(handle),
  };
  return { seams, lastLayer: () => last };
}

export async function mountCard(
  config: Partial<CardConfig>,
  fake: FakeHass,
  seams = makeSeams(),
): Promise<{ card: Card; seams: FakeSeams }> {
  const card = document.createElement(TAG) as Card;
  card.seams = seams.seams;
  card.setConfig({ type: `custom:${TAG}`, ...config });
  card.hass = fake.hass;
  document.body.append(card);
  await settle(card);
  return { card, seams };
}

/** Let fetches, decodes and renders run (works with real and fake timers). */
export async function settle(card: Card, ms = 0): Promise<void> {
  if (vi.isFakeTimers()) await vi.advanceTimersByTimeAsync(ms);
  for (let round = 0; round < 10; round += 1) {
    await Promise.resolve();
    await new Promise((resolve) => queueMicrotask(() => resolve(undefined)));
  }
  await card.updateComplete;
}

export function query<T extends Element = HTMLElement>(card: Card, selector: string): T {
  const element = card.shadowRoot.querySelector<T>(selector);
  if (!element) throw new Error(`no ${selector} in the card`);
  return element;
}

export function text(card: Card, selector: string): string {
  return query(card, selector).textContent?.replace(/\s+/g, " ").trim() ?? "";
}
