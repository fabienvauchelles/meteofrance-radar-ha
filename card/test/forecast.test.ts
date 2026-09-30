// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type Card,
  makeForecast,
  makeFrames,
  makeHass,
  makeResponse,
  mountCard,
  query,
  settle,
  text,
} from "./harness";

// Five observed frames up to 10:30 UTC (12:30 in Paris), then four forecast steps.
const LEADS = [5, 10, 45, 75];
const WITH_FORECAST = makeResponse(makeFrames(5), { forecast: makeForecast(LEADS) });

function slider(card: Card): HTMLInputElement {
  return query<HTMLInputElement>(card, "input[type=range]");
}

async function scrubTo(card: Card, index: number): Promise<void> {
  const range = slider(card);
  range.value = String(index);
  range.dispatchEvent(new Event("input"));
  range.dispatchEvent(new Event("change"));
  await settle(card);
}

function has(card: Card, selector: string): boolean {
  return card.shadowRoot.querySelector(selector) !== null;
}

beforeEach(() => {
  vi.useFakeTimers({ now: Date.parse("2026-09-30T10:33:00Z") });
  vi.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  document.body.replaceChildren();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("forecast playback", () => {
  it("appends the forecast, rests on now and marks forecast frames in English", async () => {
    const { card, seams } = await mountCard(
      { autoplay: false },
      makeHass(() => WITH_FORECAST),
    );

    expect(slider(card).max).toBe("8");
    expect(slider(card).value).toBe("4");
    expect(text(card, ".time")).toBe("30/09/26 12:30");
    expect(has(card, ".badge")).toBe(false);
    expect(has(card, ".banner")).toBe(false);
    expect(query(card, ".stage").classList.contains("forecast")).toBe(false);
    const marker = query(card, ".now-marker");
    expect(marker.style.left).toBe("50%");
    expect(marker.title).toBe("Now");
    expect(query(card, ".forecast-track").style.left).toBe("50%");

    query(card, "button.forward").click();
    await settle(card);
    expect(text(card, ".time")).toBe("30/09/26 12:35");
    expect(text(card, ".badge")).toBe("Forecast +5 min");
    expect(text(card, ".banner")).toBe("Forecast");
    expect(query(card, ".banner").getAttribute("role")).toBe("note");
    expect(query(card, ".stage").classList.contains("forecast")).toBe(true);
    expect(seams.lastLayer()).toBe(WITH_FORECAST.forecast?.frames[0]?.url);

    await scrubTo(card, 7);
    expect(text(card, ".badge")).toBe("Forecast +45 min");
    await scrubTo(card, 8);
    expect(text(card, ".badge")).toBe("Forecast +1 h 15");
    expect(text(card, ".time")).toBe("30/09/26 13:45");

    await scrubTo(card, 2);
    expect(has(card, ".badge")).toBe(false);
    expect(has(card, ".banner")).toBe(false);
  });

  it("says Prévision in French", async () => {
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => WITH_FORECAST, "fr"),
    );
    expect(query(card, ".now-marker").title).toBe("Maintenant");
    await scrubTo(card, 7);
    expect(text(card, ".badge")).toBe("Prévision +45 min");
    expect(text(card, ".banner")).toBe("Prévision");
    await scrubTo(card, 8);
    expect(text(card, ".badge")).toBe("Prévision +1 h 15");
    expect(text(card, ".time")).toBe("30/09/26 13h45");
  });

  it("plays from the first observed frame into the forecast", async () => {
    const response = makeResponse(makeFrames(2), { forecast: makeForecast([5, 10]) });
    const { card, seams } = await mountCard(
      { frame_duration_ms: 500, crossfade_ms: 0 },
      makeHass(() => response),
    );
    expect(text(card, ".time")).toBe("30/09/26 12:25");
    await settle(card, 600);
    expect(text(card, ".time")).toBe("30/09/26 12:30");
    expect(has(card, ".badge")).toBe(false);
    await settle(card, 500);
    expect(text(card, ".badge")).toBe("Forecast +5 min");
    expect(seams.lastLayer()).toBe(response.forecast?.frames[0]?.url);
  });

  it("drops the forecast when show_forecast is false", async () => {
    const { card } = await mountCard(
      { autoplay: false, show_forecast: false },
      makeHass(() => WITH_FORECAST),
    );
    expect(slider(card).max).toBe("4");
    expect(slider(card).value).toBe("4");
    expect(has(card, ".now-marker")).toBe(false);
    query(card, "button.forward").click();
    await settle(card);
    expect(text(card, ".time")).toBe("30/09/26 12:10");
    expect(has(card, ".badge")).toBe(false);
  });

  it("behaves like 0.1.0 when the server sends no forecast", async () => {
    const legacy = makeResponse(makeFrames(5));
    delete legacy.forecast;
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => legacy),
    );
    expect(slider(card).max).toBe("4");
    expect(text(card, ".time")).toBe("30/09/26 12:30");
    expect(has(card, ".now-marker")).toBe(false);
    expect(has(card, ".banner")).toBe(false);
  });

  it("ignores forecast steps that are not after the last observed frame", async () => {
    const stale = makeResponse(makeFrames(5), { forecast: makeForecast([-5, 0, 5]) });
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => stale),
    );
    expect(slider(card).max).toBe("5");
    expect(query(card, ".now-marker").style.left).toBe("80%");
  });
});
