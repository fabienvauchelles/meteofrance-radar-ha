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

const RESPONSE = makeResponse(makeFrames(3), { forecast: makeForecast([45]) });

/** Every visible string of a card resting on its first forecast frame. */
async function visibleStrings(card: Card): Promise<Record<string, string>> {
  query(card, "button.forward").click();
  await settle(card);
  return {
    time: text(card, ".time"),
    credit: text(card, ".credit"),
    badge: text(card, ".badge"),
    banner: text(card, ".banner"),
    now: query(card, ".now-marker").title,
    play: query(card, "button.play").getAttribute("aria-label") ?? "",
    back: query(card, "button.back").title,
    pin: query(card, ".pin").title,
    periods: text(card, ".periods"),
    legend: query(card, ".legend").getAttribute("aria-label") ?? "",
    noData: text(card, ".legend-item:last-child"),
    attribution: text(card, ".attribution"),
  };
}

const FRENCH = {
  time: "30/09/26 13h15",
  credit: "Données Météo-France",
  badge: "Prévision +45 min",
  banner: "Prévision",
  now: "Maintenant",
  play: "Lecture",
  back: "Image précédente",
  pin: "Maison",
  periods: "3 h 24 h 7 j 30 j Tout",
  legend: "Intensité de pluie",
  noData: "pas de données",
  attribution: "Radar : Météo-France | Fond de carte : IGN ADMIN EXPRESS 2018, Natural Earth",
};

const ENGLISH = {
  time: "30/09/26 13:15",
  credit: "Météo-France data",
  badge: "Forecast +45 min",
  banner: "Forecast",
  now: "Now",
  play: "Play",
  back: "Previous image",
  pin: "Home",
  periods: "3 h 24 h 7 d 30 d All",
  legend: "Rain rate",
  noData: "no data",
  attribution: "Radar: Météo-France | Basemap: IGN ADMIN EXPRESS 2018, Natural Earth",
};

beforeEach(() => {
  vi.useFakeTimers({ now: Date.parse("2026-09-30T10:33:00Z") });
  vi.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  document.body.replaceChildren();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the card language follows the Home Assistant profile", () => {
  it.each(["fr", "fr-FR"])("is French for %s", async (language) => {
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => RESPONSE, language),
    );
    expect(await visibleStrings(card)).toEqual(FRENCH);
  });

  it.each(["en", "de"])("is English for %s", async (language) => {
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => RESPONSE, language),
    );
    expect(await visibleStrings(card)).toEqual(ENGLISH);
  });

  it("prefers the profile locale over the older language field", async () => {
    const fake = makeHass(() => RESPONSE, "fr");
    fake.hass.language = "en";
    const { card } = await mountCard({ autoplay: false }, fake);
    expect((await visibleStrings(card)).banner).toBe("Prévision");
  });

  it("falls back to the older language field without a locale", async () => {
    const fake = makeHass(() => RESPONSE, "fr");
    delete fake.hass.locale;
    const { card } = await mountCard({ autoplay: false }, fake);
    expect((await visibleStrings(card)).banner).toBe("Prévision");
  });

  it("switches language when the user changes it", async () => {
    const fake = makeHass(() => RESPONSE, "en");
    const { card } = await mountCard({ autoplay: false }, fake);
    expect(text(card, ".credit")).toBe("Météo-France data");
    card.hass = { ...fake.hass, locale: { language: "fr" } };
    await settle(card);
    expect(text(card, ".credit")).toBe("Données Météo-France");
  });
});
