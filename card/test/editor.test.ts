// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { TAG } from "./harness";

type CardClass = {
  getConfigForm(): {
    schema: { name: string; selector: Record<string, Record<string, unknown>> }[];
    computeLabel(field: { name: string }): string | undefined;
    computeHelper(field: { name: string }): string | undefined;
    assertConfig(config: Record<string, unknown>): void;
  };
  getStubConfig(): Record<string, unknown>;
};

function cardClass(): CardClass {
  return customElements.get(TAG) as unknown as CardClass;
}

function withLanguage(language: string): void {
  const root = document.createElement("home-assistant") as HTMLElement & { hass?: unknown };
  root.hass = { locale: { language } };
  document.body.append(root);
}

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe("getConfigForm", () => {
  it("offers the five options with their selectors and English labels", () => {
    withLanguage("en");
    const form = cardClass().getConfigForm();
    expect(form.schema.map((field) => field.name)).toEqual([
      "default_period",
      "autoplay",
      "show_legend",
      "frame_duration_ms",
      "crossfade_ms",
    ]);
    const period = form.schema[0]?.selector.select as { options: { value: string }[] };
    expect(period.options.map((option) => option.value)).toEqual(["3h", "24h", "7d", "30d", "all"]);
    expect(form.schema[1]?.selector).toEqual({ boolean: {} });
    expect(form.schema[3]?.selector.number).toMatchObject({ min: 100, max: 5000 });
    expect(form.schema[4]?.selector.number).toMatchObject({ min: 0, max: 2000 });
    expect(form.computeLabel({ name: "autoplay" })).toBe("Play on load");
    expect(form.computeHelper({ name: "crossfade_ms" })).toContain("never longer");
    expect(form.computeHelper({ name: "autoplay" })).toBeUndefined();
  });

  it("labels the form in French for a French frontend", () => {
    withLanguage("fr");
    const form = cardClass().getConfigForm();
    expect(form.computeLabel({ name: "default_period" })).toBe("Période par défaut");
    expect(form.computeLabel({ name: "show_legend" })).toBe("Afficher la légende");
    const period = form.schema[0]?.selector.select as { options: { label: string }[] };
    expect(period.options.map((option) => option.label)).toContain("Tout");
  });

  it("falls back to the browser language outside a Home Assistant page", () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("fr-FR");
    expect(cardClass().getConfigForm().computeLabel({ name: "autoplay" })).toBe(
      "Lecture automatique",
    );
  });

  it("sends a config it cannot show back to the YAML editor", () => {
    const form = cardClass().getConfigForm();
    expect(() => form.assertConfig({ type: `custom:${TAG}`, frame_duration_ms: 1 })).toThrow();
    expect(() => form.assertConfig({ type: `custom:${TAG}`, crossfade_ms: 100 })).not.toThrow();
  });
});

describe("getStubConfig", () => {
  it("gives a config the card accepts", () => {
    const stub = cardClass().getStubConfig();
    expect(stub).toEqual({ default_period: "3h", autoplay: true });
    const card = document.createElement(TAG) as HTMLElement & { setConfig(c: unknown): void };
    expect(() => card.setConfig({ type: `custom:${TAG}`, ...stub })).not.toThrow();
  });
});
