// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CardConfig } from "../src/config";
import {
  type Card,
  makeFrames,
  makeHass,
  makeResponse,
  mountCard,
  query,
  settle,
  TAG,
  text,
} from "./harness";

const TEN = makeResponse(makeFrames(10));

function slider(card: Card): HTMLInputElement {
  return query<HTMLInputElement>(card, "input[type=range]");
}

async function click(card: Card, selector: string): Promise<void> {
  query(card, selector).click();
  await settle(card);
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

describe("registration", () => {
  it("defines the element once and lists it in the card picker", () => {
    expect(customElements.get(TAG)).toBeTruthy();
    const cards = (window as unknown as { customCards: { type: string; preview?: boolean }[] })
      .customCards;
    const entries = cards.filter((entry) => entry.type === TAG);
    expect(entries).toHaveLength(1);
    expect(entries[0]?.preview).toBe(true);
    const card = document.createElement(TAG) as Card;
    expect(card.getCardSize()).toBe(7);
    expect(card.getGridOptions()).toMatchObject({ columns: 12, rows: "auto" });
  });
});

describe("setConfig", () => {
  const base = { type: `custom:${TAG}` };
  it.each([
    [{ bogus: 1 }],
    [{ default_period: "1h" }],
    [{ autoplay: "yes" }],
    [{ show_legend: 1 }],
    [{ frame_duration_ms: 50 }],
    [{ frame_duration_ms: "500" }],
    [{ crossfade_ms: 2500 }],
  ])("rejects %j", (extra) => {
    const card = document.createElement(TAG) as Card;
    expect(() => card.setConfig({ ...base, ...extra } as CardConfig)).toThrow();
  });

  it("accepts every documented option and the dashboard layout keys", () => {
    const card = document.createElement(TAG) as Card;
    expect(() =>
      card.setConfig({
        ...base,
        default_period: "7d",
        autoplay: false,
        show_legend: false,
        frame_duration_ms: 200,
        crossfade_ms: 2000,
        grid_options: { columns: 6 },
        visibility: [],
      }),
    ).not.toThrow();
  });
});

describe("a loaded card", () => {
  it("shows the latest frame, the controls, the legend and the credits", async () => {
    const fake = makeHass(() => TEN);
    const { card, seams } = await mountCard({ autoplay: false }, fake);

    expect(fake.callApi).toHaveBeenCalledWith("GET", "meteofrance_radar/frames?period=3h");
    expect(text(card, ".time")).toBe("30/09/26 12:30");
    expect(text(card, ".credit")).toBe("Météo-France data");
    expect(card.shadowRoot.querySelector(".gap")).toBeNull();
    expect(slider(card).max).toBe("9");
    expect(slider(card).value).toBe("9");
    expect(query(card, "button.play").getAttribute("aria-label")).toBe("Play");
    const chips = [...card.shadowRoot.querySelectorAll<HTMLElement>(".chip")];
    expect(chips.map((chip) => chip.textContent?.trim())).toEqual([
      "3 h",
      "24 h",
      "7 d",
      "30 d",
      "All",
    ]);
    expect(query(card, '.chip[data-period="3h"]').getAttribute("aria-pressed")).toBe("true");
    expect(card.shadowRoot.querySelectorAll(".legend-item")).toHaveLength(11);
    expect(text(card, ".legend")).toContain("mm/h");
    expect(text(card, ".attribution")).toBe(
      "Radar: Météo-France | Basemap: IGN ADMIN EXPRESS 2018, Natural Earth",
    );
    expect(seams.lastLayer()).toBe(TEN.frames[9]?.url);
    expect(fake.fetchWithAuth).toHaveBeenCalledWith("/meteofrance_radar/basemap.png?v=0.1.0");
  });

  it("hides the legend when the config says so", async () => {
    const { card } = await mountCard(
      { autoplay: false, show_legend: false },
      makeHass(() => TEN),
    );
    expect(card.shadowRoot.querySelector(".legend")).toBeNull();
  });

  it("plays from the first frame and advances one frame per frame_duration_ms", async () => {
    const config = { frame_duration_ms: 500, crossfade_ms: 0 };
    const { card, seams } = await mountCard(
      config,
      makeHass(() => TEN),
    );
    expect(text(card, ".time")).toBe("30/09/26 11:45");
    expect(query(card, "button.play").getAttribute("aria-label")).toBe("Pause");

    await settle(card, 600);
    expect(text(card, ".time")).toBe("30/09/26 11:50");
    await settle(card, 500);
    expect(text(card, ".time")).toBe("30/09/26 11:55");
    expect(slider(card).value).toBe("2");
    expect(seams.lastLayer()).toBe(TEN.frames[2]?.url);

    await click(card, "button.play");
    await settle(card, 2000);
    expect(text(card, ".time")).toBe("30/09/26 11:55");
  });

  it("resumes a playing loop when the card comes back into view", async () => {
    const config = { frame_duration_ms: 500, crossfade_ms: 0 };
    const { card } = await mountCard(
      config,
      makeHass(() => TEN),
    );
    await settle(card, 600);
    card.remove();
    document.body.append(card);
    await settle(card, 500);
    expect(query(card, "button.play").getAttribute("aria-label")).toBe("Pause");
    expect(text(card, ".time")).toBe("30/09/26 11:55");
  });

  it("steps back and forward, scrubs, and refetches on a period switch", async () => {
    const fake = makeHass((period) => (period === "24h" ? makeResponse(makeFrames(20)) : TEN));
    const { card } = await mountCard({ autoplay: false }, fake);

    await click(card, "button.back");
    expect(text(card, ".time")).toBe("30/09/26 12:25");
    await click(card, "button.forward");
    await click(card, "button.forward");
    expect(text(card, ".time")).toBe("30/09/26 11:45");
    expect(slider(card).value).toBe("0");

    const range = slider(card);
    range.value = "4";
    range.dispatchEvent(new Event("input"));
    range.dispatchEvent(new Event("change"));
    await settle(card);
    expect(text(card, ".time")).toBe("30/09/26 12:05");

    await click(card, '.chip[data-period="24h"]');
    expect(fake.periods).toEqual(["3h", "24h"]);
    expect(query(card, '.chip[data-period="24h"]').getAttribute("aria-pressed")).toBe("true");
    expect(slider(card).max).toBe("19");
  });

  it("marks a skipped gap in English and in French", async () => {
    const gapped = makeResponse(makeFrames(10, undefined, { 9: 25 }));
    const en = await mountCard(
      { autoplay: false },
      makeHass(() => gapped),
    );
    expect(text(en.card, ".gap")).toBe("gap of 25 min skipped");

    const fr = await mountCard(
      { autoplay: false },
      makeHass(() => gapped, "fr"),
    );
    expect(text(fr.card, ".gap")).toBe("saut de 25 min");
    expect(text(fr.card, ".time")).toBe("30/09/26 12h30");
    expect(text(fr.card, ".credit")).toBe("Données Météo-France");
    expect(text(fr.card, '.chip[data-period="7d"]')).toBe("7 j");
  });
});

describe("the home pin", () => {
  it("sits at the pixel given by the API, as percentages of the map", async () => {
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => TEN),
    );
    const pin = query(card, ".pin");
    expect(pin.hidden).toBe(false);
    expect(pin.style.left).toBe("50%");
    expect(pin.style.top).toBe("25%");
  });

  it.each([
    ["outside the map", { x: 2500, y: 100, inside: false }],
    ["unknown", null],
  ])("is hidden when %s", async (_label, pin) => {
    const response = makeResponse(makeFrames(3), { pin });
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => response),
    );
    expect(query(card, ".pin").hidden).toBe(true);
  });
});

describe("empty, error and refresh", () => {
  it("says there is no image yet on an empty archive", async () => {
    const { card } = await mountCard(
      {},
      makeHass(() => makeResponse([])),
    );
    expect(text(card, ".message")).toContain("No radar image yet");
    expect(query<HTMLButtonElement>(card, "button.play").disabled).toBe(true);
    expect(card.shadowRoot.querySelector(".time")).toBeNull();
  });

  it("refreshes an empty archive without flashing the loading message", async () => {
    let calls = 0;
    const fake = makeHass(() => {
      calls += 1;
      return calls === 1 ? makeResponse([]) : new Error("HTTP 500");
    });
    const { card } = await mountCard({}, fake);
    await settle(card, 60_000);
    expect(text(card, ".message")).toContain("No radar image yet");
  });

  it("shows an error, then recovers at the next refresh", async () => {
    const fake = makeHass(() => new Error("HTTP 503"), "fr");
    const { card } = await mountCard({ autoplay: false }, fake);
    expect(text(card, ".message.error")).toContain("Impossible de charger");

    fake.respond(() => TEN);
    await settle(card, 60_000);
    expect(card.shadowRoot.querySelector(".message")).toBeNull();
    expect(text(card, ".time")).toBe("30/09/26 12h30");
  });

  it("keeps the frame on screen when the list refreshes every minute", async () => {
    const fake = makeHass(() => TEN);
    const { card } = await mountCard({ autoplay: false }, fake);
    await click(card, "button.back");
    await click(card, "button.back");
    expect(text(card, ".time")).toBe("30/09/26 12:20");

    fake.respond(() => makeResponse(makeFrames(10, "2026-09-30T10:35:00Z")));
    await settle(card, 60_000);
    expect(fake.callApi).toHaveBeenCalledTimes(2);
    expect(text(card, ".time")).toBe("30/09/26 12:20");
    expect(slider(card).value).toBe("6");

    fake.respond(() => new Error("HTTP 500"));
    await settle(card, 60_000);
    expect(card.shadowRoot.querySelector(".message")).toBeNull();
    expect(text(card, ".time")).toBe("30/09/26 12:20");
  });
});
