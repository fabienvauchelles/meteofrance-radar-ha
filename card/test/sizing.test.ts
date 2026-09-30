// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CardConfig } from "../src/config";
import { cardStyles } from "../src/styles";
import { type Card, makeFrames, makeHass, makeResponse, mountCard, query, TAG } from "./harness";

const RESPONSE = makeResponse(makeFrames(3));

/** Declarations of the first rule whose selector list holds exactly `selector`. */
function rule(selector: string): string {
  const css = cardStyles.cssText.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const block of css.split("}")) {
    const [head, body] = block.split("{");
    const selectors = (head ?? "").split(",").map((part) => part.trim());
    if (body !== undefined && selectors.includes(selector)) return body.replace(/\s+/g, " ");
  }
  throw new Error(`no rule for ${selector}`);
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

describe("card sizing in a sections view", () => {
  it("asks for the full width and allows half a section", () => {
    const card = document.createElement(TAG) as HTMLElement & {
      getGridOptions(): Record<string, unknown>;
    };
    expect(card.getGridOptions()).toEqual({
      columns: 12,
      rows: "auto",
      min_columns: 6,
      min_rows: 4,
    });
  });

  it("keeps a 16:9 stage with automatic rows", async () => {
    const { card } = await mountCard(
      { autoplay: false, grid_options: { columns: 6, rows: "auto" } },
      makeHass(() => RESPONSE),
    );
    expect(query(card, "ha-card").classList.contains("fill")).toBe(false);
    expect(query(card, ".stage").style.aspectRatio).toContain(String(16 / 9));
  });

  it("fills a fixed number of rows with a map that keeps its ratio", async () => {
    const { card } = await mountCard(
      { autoplay: false, grid_options: { columns: 6, rows: 5 } },
      makeHass(() => RESPONSE),
    );
    expect(query(card, "ha-card").classList.contains("fill")).toBe(true);
    expect(query(card, ".stage").style.aspectRatio).toBe("");
    expect(query(card, ".stage > .map > canvas")).toBeTruthy();
    expect(query(card, ".map > .pin")).toBeTruthy();
    expect(rule("ha-card.fill .stage")).toContain("container-type: size");
    expect(query(card, ".stage").style.getPropertyValue("--map-aspect")).toBe(String(16 / 9));
    expect(rule("ha-card.fill .map")).toContain("calc(100cqh * var(--map-aspect, 16 / 9))");
    expect(rule("ha-card.fill .map")).toContain("aspect-ratio: var(--map-aspect, 16 / 9)");
  });

  it("wraps the controls, the slider taking the room left by the buttons", async () => {
    const { card } = await mountCard(
      { autoplay: false },
      makeHass(() => RESPONSE),
    );
    expect(query(card, ".controls > .slider > input[type=range]")).toBeTruthy();
    expect(rule(".controls")).toContain("flex-wrap: wrap");
    expect(rule(".slider")).toContain("flex: 1 1 140px");
    expect(rule(".controls button")).toContain("flex: none");
  });
});

type PanelCard = Card & { layout?: string; isPanel?: boolean };

async function mountPanel(set: (card: PanelCard) => void, config: Partial<CardConfig> = {}) {
  const { card } = await mountCard(
    { autoplay: false, ...config },
    makeHass(() => RESPONSE),
  );
  const panel = card as PanelCard;
  set(panel);
  await panel.updateComplete;
  return panel;
}

describe("card sizing in a panel view", () => {
  it("fits under the header when hui-card sets the panel layout", async () => {
    const card = await mountPanel((panel) => {
      panel.layout = "panel";
    });
    expect(card.hasAttribute("panel")).toBe(true);
    expect(query(card, "ha-card").className).toBe("panel");
    const stage = query(card, ".stage");
    expect(stage.style.aspectRatio).toContain(String(16 / 9));
    expect(stage.style.getPropertyValue("--map-aspect")).toBe(String(16 / 9));
    expect(query(card, ".stage > .map > .pin")).toBeTruthy();
    expect(rule(":host([panel])")).toContain("height: auto");
    const box = rule("ha-card.panel");
    expect(box).toContain("flex-direction: column");
    expect(box).toContain("max-height: calc( 100dvh - var(--header-height, 56px)");
    expect(rule("ha-card.panel > *")).toContain("flex: none");
    const stageRule = rule("ha-card.panel .stage");
    expect(stageRule).toContain("flex: 0 1 auto");
    expect(stageRule).toContain("min-height: 0");
    expect(stageRule).toContain("container-type: size");
    expect(rule("ha-card.panel .map")).toContain("calc(100cqh * var(--map-aspect, 16 / 9))");
  });

  it("takes the older isPanel flag and wins over numeric grid rows", async () => {
    const card = await mountPanel(
      (panel) => {
        panel.isPanel = true;
      },
      { grid_options: { columns: 12, rows: 6 } },
    );
    expect(query(card, "ha-card").className).toBe("panel");
    expect(query(card, ".stage").style.aspectRatio).toContain(String(16 / 9));
  });

  it("goes back to the sections sizing when the layout changes", async () => {
    const card = await mountPanel((panel) => {
      panel.layout = "panel";
    });
    card.layout = "grid";
    await card.updateComplete;
    expect(card.hasAttribute("panel")).toBe(false);
    expect(query(card, "ha-card").className).toBe("");
  });
});
