// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cardStyles } from "../src/styles";
import { makeFrames, makeHass, makeResponse, mountCard, query, TAG } from "./harness";

const RESPONSE = makeResponse(makeFrames(3));

/** Declarations of the first rule whose selector is exactly `selector`. */
function rule(selector: string): string {
  const css = cardStyles.cssText;
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = new RegExp(`(?:^|\\})\\s*${escaped}\\s*\\{([^}]*)\\}`).exec(css);
  if (!match?.[1]) throw new Error(`no rule for ${selector}`);
  return match[1].replace(/\s+/g, " ");
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
