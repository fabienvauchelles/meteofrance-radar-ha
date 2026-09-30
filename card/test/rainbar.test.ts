// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MeteoFranceRainBarCard } from "../src/rainbar/card";
import type { RainBarConfig } from "../src/rainbar/config";
import {
  all,
  BAR_TAG,
  type BarCard,
  COLORS,
  makeBarHass,
  makeSeries,
  mountBar,
  NOW,
  one,
  percent,
  settleBar,
} from "./rainbar-harness";

beforeEach(() => {
  vi.useFakeTimers({ now: Date.parse(NOW) });
  vi.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  document.body.replaceChildren();
  document.documentElement.lang = "";
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function labels(card: BarCard): string[] {
  return all(card, ".tick").map((tick) => tick.textContent?.trim() ?? "");
}

function segmentBy(card: BarCard, source: string, index = 0): HTMLElement {
  const found = all(card, ".segment").filter((element) => element.dataset.source === source);
  const element = found[index];
  if (!element) throw new Error(`no ${source} segment ${index}`);
  return element;
}

describe("registration", () => {
  it("defines both cards once and lists both in the card picker", () => {
    expect(customElements.get(BAR_TAG)).toBe(MeteoFranceRainBarCard);
    const cards = (window as unknown as { customCards: { type: string; preview?: boolean }[] })
      .customCards;
    for (const type of [BAR_TAG, "meteofrance-radar-card"]) {
      expect(cards.filter((entry) => entry.type === type)).toHaveLength(1);
    }
    expect(cards.find((entry) => entry.type === BAR_TAG)?.preview).toBe(true);
    const card = document.createElement(BAR_TAG) as BarCard;
    expect(card.getCardSize()).toBe(2);
    expect(card.getGridOptions()).toEqual({
      columns: 12,
      rows: "auto",
      min_columns: 3,
      min_rows: 1,
    });
    expect(MeteoFranceRainBarCard.getStubConfig()).toEqual({});
  });
});

describe("bar", () => {
  it("draws the segments at their place with the legend colours", async () => {
    const fake = makeBarHass();
    const card = await mountBar({}, fake);
    expect(fake.callApi).toHaveBeenCalledWith("GET", "meteofrance_radar/pin_series");
    expect(all(card, ".segment")).toHaveLength(6);

    const dry = segmentBy(card, "radar", 0);
    expect(percent(dry, "left")).toBeCloseTo(0);
    expect(percent(dry, "width")).toBeCloseTo(100 / 120);
    expect(dry.getAttribute("style")).not.toContain("background-color");

    const nodata = segmentBy(card, "radar", 1);
    expect(nodata.classList.contains("nodata")).toBe(true);
    expect(nodata.getAttribute("style")).toContain("background-color:#808080");

    const piaf = segmentBy(card, "piaf");
    expect(percent(piaf, "left")).toBeCloseTo((185 / 600) * 100);
    expect(piaf.getAttribute("style")).toContain(`background-color:${COLORS[2]}`);

    const arome = segmentBy(card, "arome");
    expect(percent(arome, "left")).toBeCloseTo(90);
    expect(percent(arome, "width")).toBeCloseTo(10);
    expect(arome.getAttribute("style")).toContain(`background-color:${COLORS[0]}`);
  });

  it("hatches the forecast segments only", async () => {
    const card = await mountBar({}, makeBarHass());
    for (const element of all(card, ".segment")) {
      const forecast = element.dataset.source !== "radar";
      expect(element.classList.contains("forecast")).toBe(forecast);
    }
    expect(all(card, ".segment.forecast")).toHaveLength(3);
    for (const element of all(card, ".segment")) {
      expect(element.classList.contains("dry")).toBe(element.dataset.class === "0");
    }
  });

  it("draws the now line on the client clock and moves it every minute", async () => {
    const card = await mountBar({}, makeBarHass());
    const line = one(card, ".now");
    expect(line.title).toBe("Now");
    expect(percent(line, "left")).toBeCloseTo(31.2);
    await settleBar(card, 360_000);
    expect(percent(one(card, ".now"), "left")).toBeCloseTo(32.2);
  });

  it("labels the hours in the Home Assistant time zone", async () => {
    const english = await mountBar({}, makeBarHass());
    expect(labels(english)).toEqual(["14:00", "16:00", "18:00", "20:00", "22:00", "00:00"]);
    document.body.replaceChildren();
    const french = await mountBar({}, makeBarHass(undefined, "fr"));
    expect(labels(french)).toEqual(["14h", "16h", "18h", "20h", "22h", "00h"]);
    document.body.replaceChildren();
    const utc = await mountBar({}, makeBarHass(undefined, "en", "UTC"));
    expect(labels(utc)[0]).toBe("12:00");
  });

  it("gives each segment a localised tooltip", async () => {
    const english = await mountBar({}, makeBarHass());
    const piaf = segmentBy(english, "piaf");
    expect(piaf.title).toBe("17:05-17:10 · 1.2 mm/h");
    expect(piaf.getAttribute("aria-label")).toBe(piaf.title);
    expect(segmentBy(english, "radar", 1).title).toBe("14:05-14:10 · no data");
    document.body.replaceChildren();

    const french = await mountBar({}, makeBarHass(undefined, "fr-FR"));
    expect(segmentBy(french, "piaf").title).toBe("17h05-17h10 · 1,2 mm/h");
    expect(segmentBy(french, "radar", 1).title).toBe("14h05-14h10 · pas de données");
    expect(one(french, ".now").title).toBe("Maintenant");
  });

  it("shows the title, the credit and the legend only when asked, and no summary", async () => {
    const plain = await mountBar({}, makeBarHass());
    expect(plain.shadowRoot.querySelector(".title")).toBeNull();
    expect(plain.shadowRoot.querySelector(".legend")).toBeNull();
    expect(one(plain, ".credit").textContent).toBe("Source: Météo-France");
    document.body.replaceChildren();

    const full = await mountBar({ title: "Pluie", show_legend: true }, makeBarHass());
    expect(one(full, ".title").textContent).toBe("Pluie");
    expect(all(full, ".legend .swatch")).toHaveLength(11);
    const text = one(full, "ha-card").textContent?.replace(/\s+/g, " ") ?? "";
    expect(text).not.toMatch(/rain (stops|starts)|no rain/i);
  });

  it("draws an empty bar with the now line when there are no segments", async () => {
    const card = await mountBar(
      {},
      makeBarHass(() => makeSeries({ segments: [] })),
    );
    expect(all(card, ".segment")).toHaveLength(0);
    expect(one(card, ".now")).toBeTruthy();
  });
});

describe("states", () => {
  it("asks for the home location when Home Assistant has none", async () => {
    const located = () => makeSeries({ located: false, segments: [] });
    const english = await mountBar({}, makeBarHass(located));
    expect(one(english, ".message").textContent).toBe(
      "Set your home location in the Home Assistant settings.",
    );
    expect(english.shadowRoot.querySelector(".bar")).toBeNull();
    document.body.replaceChildren();
    const french = await mountBar({}, makeBarHass(located, "fr"));
    expect(one(french, ".message").textContent).toContain("paramètres de Home Assistant");
  });

  it("shows the loading message before the first answer", async () => {
    const fake = makeBarHass();
    fake.callApi.mockImplementation(() => new Promise(() => {}));
    const card = await mountBar({}, fake);
    expect(one(card, ".message.loading").textContent).toBe("Loading the rain forecast...");
  });

  it("shows an error, then recovers at the next refresh", async () => {
    const fake = makeBarHass(() => new Error("HTTP 503"));
    const card = await mountBar({}, fake);
    expect(one(card, "[role=alert]").textContent).toContain("Could not load");
    fake.respond(() => makeSeries());
    await settleBar(card, 300_000);
    expect(card.shadowRoot.querySelector("[role=alert]")).toBeNull();
    expect(all(card, ".segment")).toHaveLength(6);
  });
});

describe("refresh", () => {
  it("fetches on connect and every 5 minutes, and stops once removed", async () => {
    const fake = makeBarHass();
    const card = await mountBar({}, fake);
    expect(fake.callApi).toHaveBeenCalledTimes(1);
    card.hass = { ...fake.hass };
    await settleBar(card, 240_000);
    expect(fake.callApi).toHaveBeenCalledTimes(1);
    await settleBar(card, 60_000);
    expect(fake.callApi).toHaveBeenCalledTimes(2);
    await settleBar(card, 300_000);
    expect(fake.callApi).toHaveBeenCalledTimes(3);
    card.remove();
    await settleBar(card, 900_000);
    expect(fake.callApi).toHaveBeenCalledTimes(3);
  });
});

describe("config", () => {
  const base = { type: `custom:${BAR_TAG}` };

  it.each([[{ bogus: 1 }], [{ title: 3 }], [{ show_legend: "yes" }]])("refuses %j", (extra) => {
    const card = document.createElement(BAR_TAG) as BarCard;
    expect(() => card.setConfig({ ...base, ...extra } as RainBarConfig)).toThrow();
  });

  it("accepts the layout keys Home Assistant adds", () => {
    const card = document.createElement(BAR_TAG) as BarCard;
    expect(() =>
      card.setConfig({ ...base, grid_options: { columns: 6 }, visibility: [], view_layout: {} }),
    ).not.toThrow();
  });

  it("builds the form with labels in the frontend language", () => {
    document.documentElement.lang = "";
    const root = document.createElement("home-assistant") as HTMLElement & {
      hass?: unknown;
    };
    root.hass = { locale: { language: "fr" } };
    document.body.append(root);
    const form = MeteoFranceRainBarCard.getConfigForm();
    expect(form.schema).toEqual([
      { name: "title", selector: { text: {} } },
      { name: "show_legend", selector: { boolean: {} } },
    ]);
    expect(form.computeLabel({ name: "title" })).toBe("Titre");
    expect(form.computeLabel({ name: "show_legend" })).toBe("Afficher la légende");
    expect(() => form.assertConfig({ ...base, bogus: true })).toThrow("unknown option: bogus");
    root.hass = { locale: { language: "en" } };
    expect(MeteoFranceRainBarCard.getConfigForm().computeLabel({ name: "title" })).toBe("Title");
  });
});
