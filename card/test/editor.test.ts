// @vitest-environment jsdom
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { ensureHaForm } from "../src/ha-form-loader";
import type { HomeAssistant } from "../src/types";
import { TAG } from "./harness";

type Field = { name: string; selector: Record<string, Record<string, unknown>> };

/** Stand-in for Home Assistant's ha-form: keeps what the editor hands it. */
class StubHaForm extends HTMLElement {
  data: Record<string, unknown> = {};
  schema: Field[] = [];
  hass: unknown;
  computeLabel: (field: { name: string }) => string | undefined = () => undefined;
  computeHelper: (field: { name: string }) => string | undefined = () => undefined;
}

type Editor = HTMLElement & {
  hass: HomeAssistant;
  setConfig(config: Record<string, unknown>): void;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

type CardClass = {
  getConfigElement(): Promise<Editor>;
  getStubConfig(): Record<string, unknown>;
  getConfigForm?: unknown;
};

function cardClass(): CardClass {
  return customElements.get(TAG) as unknown as CardClass;
}

function hassIn(language: string): HomeAssistant {
  return { locale: { language }, language, config: {} } as unknown as HomeAssistant;
}

async function openEditor(
  config: Record<string, unknown>,
  language = "en",
): Promise<{ editor: Editor; form: StubHaForm }> {
  const editor = await cardClass().getConfigElement();
  editor.hass = hassIn(language);
  editor.setConfig({ type: `custom:${TAG}`, ...config });
  document.body.append(editor);
  await editor.updateComplete;
  const form = editor.shadowRoot.querySelector("ha-form") as StubHaForm | null;
  if (!form) throw new Error("the editor rendered no ha-form");
  return { editor, form };
}

beforeAll(() => {
  customElements.define("ha-form", StubHaForm);
});

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe("the editor element", () => {
  it("replaces the plain form and shows the effective defaults of an empty config", async () => {
    expect(cardClass().getConfigForm).toBeUndefined();
    const { editor, form } = await openEditor({});
    expect(editor.tagName.toLowerCase()).toBe("meteofrance-radar-card-editor");
    expect(form.data).toMatchObject({
      default_period: "3h",
      autoplay: true,
      show_legend: true,
      show_forecast: true,
      frame_duration_ms: 500,
      crossfade_ms: 300,
    });
    expect(form.schema.map((field) => field.name)).toEqual([
      "default_period",
      "autoplay",
      "show_legend",
      "show_forecast",
      "frame_duration_ms",
      "crossfade_ms",
    ]);
    const period = form.schema[0]?.selector.select as { options: { value: string }[] };
    expect(period.options.map((option) => option.value)).toEqual(["3h", "24h", "7d", "30d", "all"]);
    expect(form.schema[4]?.selector.number).toMatchObject({ min: 100, max: 5000 });
  });

  it("keeps the options the config sets", async () => {
    const { form } = await openEditor({ default_period: "7d", autoplay: false });
    expect(form.data).toMatchObject({ default_period: "7d", autoplay: false, show_legend: true });
  });

  it("emits a config stripped of defaults, keeping the layout keys", async () => {
    const { editor, form } = await openEditor({ grid_options: { columns: 6 } });
    const emitted: Record<string, unknown>[] = [];
    editor.addEventListener("config-changed", (event) => {
      emitted.push((event as CustomEvent<{ config: Record<string, unknown> }>).detail.config);
    });
    form.dispatchEvent(
      new CustomEvent("value-changed", {
        detail: { value: { ...form.data, default_period: "24h", show_forecast: false } },
      }),
    );
    expect(emitted).toEqual([
      {
        type: `custom:${TAG}`,
        grid_options: { columns: 6 },
        default_period: "24h",
        show_forecast: false,
      },
    ]);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data } } }));
    expect(emitted[1]).toEqual({ type: `custom:${TAG}`, grid_options: { columns: 6 } });
  });

  it("labels the form in English", async () => {
    const { form } = await openEditor({}, "de");
    expect(form.computeLabel({ name: "default_period" })).toBe("Default period");
    expect(form.computeLabel({ name: "show_forecast" })).toBe("Continue with the forecast");
    expect(form.computeHelper({ name: "crossfade_ms" })).toContain("never longer");
    expect(form.computeHelper({ name: "autoplay" })).toBeUndefined();
  });

  it("labels the form in French", async () => {
    const { form } = await openEditor({}, "fr");
    expect(form.computeLabel({ name: "default_period" })).toBe("Période par défaut");
    expect(form.computeLabel({ name: "show_legend" })).toBe("Afficher la légende");
    expect(form.computeLabel({ name: "show_forecast" })).toBe("Continuer avec la prévision");
    const period = form.schema[0]?.selector.select as { options: { label: string }[] };
    expect(period.options.map((option) => option.label)).toContain("Tout");
  });
});

describe("ensureHaForm", () => {
  it("asks a built-in card for its editor, then waits at most the given time", async () => {
    vi.useFakeTimers();
    const registry = {
      get: vi.fn((tag: string) =>
        tag === "hui-tile-card" ? { getConfigElement: vi.fn(async () => undefined) } : undefined,
      ),
      whenDefined: vi.fn(() => new Promise<CustomElementConstructor>(() => {})),
    } as unknown as CustomElementRegistry;
    let done = false;
    const waiting = ensureHaForm(registry, 5000).then(() => {
      done = true;
    });
    await vi.advanceTimersByTimeAsync(4999);
    expect(done).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await waiting;
    expect(done).toBe(true);
    expect(registry.get).toHaveBeenCalledWith("hui-tile-card");
    vi.useRealTimers();
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
