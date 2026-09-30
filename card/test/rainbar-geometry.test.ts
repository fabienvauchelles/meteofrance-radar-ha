import { describe, expect, it } from "vitest";
import {
  formatClock,
  formatRate,
  hourTicks,
  maxLabelsFor,
  percentOf,
  segmentTooltip,
  spanBox,
  tickStep,
} from "../src/rainbar/geometry";

const at = (clock: string): number => Date.parse(`2026-09-30T${clock}:00Z`);
const START = at("12:00");
const END = at("22:00");

describe("time to percent", () => {
  it("places times on the window and clamps outside it", () => {
    expect(percentOf(START, START, END)).toBe(0);
    expect(percentOf(at("17:00"), START, END)).toBe(50);
    expect(percentOf(at("11:00"), START, END)).toBe(0);
    expect(percentOf(at("23:00"), START, END)).toBe(100);
    expect(percentOf(START, END, START)).toBe(0);
  });

  it("gives the left edge and width of a span", () => {
    const box = spanBox(at("15:00"), at("16:00"), START, END);
    expect(box.left).toBeCloseTo(30);
    expect(box.width).toBeCloseTo(10);
    expect(spanBox(at("21:30"), at("23:00"), START, END).width).toBeCloseTo(5);
  });
});

describe("tick step", () => {
  const hours = (count: number): number[] => Array.from({ length: count }, (_, i) => i % 24);

  it("picks the smallest step that keeps at most the label budget", () => {
    expect(tickStep(hours(8), 8)).toBe(1);
    expect(tickStep(hours(10), 8)).toBe(2);
    expect(tickStep(hours(20), 8)).toBe(3);
    expect(tickStep(hours(30), 8)).toBe(6);
    expect(tickStep(hours(10), 4)).toBe(3);
  });

  it("labels even local hours in Paris and uses 6 h when even that is too dense", () => {
    const ticks = hourTicks(START, END, "Europe/Paris", "en");
    expect(ticks.map((tick) => tick.label)).toEqual([
      "14:00",
      "16:00",
      "18:00",
      "20:00",
      "22:00",
      "00:00",
    ]);
    expect(ticks[0]?.percent).toBe(0);
    expect(ticks[5]?.percent).toBe(100);
    const french = hourTicks(START, END, "Europe/Paris", "fr", 4);
    expect(french.map((tick) => tick.label)).toEqual(["15h", "18h", "21h", "00h"]);
  });

  it("follows the zone, including one with a half-hour offset", () => {
    expect(hourTicks(START, at("15:00"), "UTC", "en").map((t) => t.label)).toEqual([
      "12:00",
      "13:00",
      "14:00",
      "15:00",
    ]);
    const kolkata = hourTicks(START, at("14:00"), "Asia/Kolkata", "en");
    expect(kolkata.map((t) => t.label)).toEqual(["18:00", "19:00"]);
    expect(kolkata[0]?.percent).toBeCloseTo(25);
  });

  it("uses fewer labels on a narrow card", () => {
    expect(maxLabelsFor(0)).toBe(8);
    expect(maxLabelsFor(300)).toBe(4);
    expect(maxLabelsFor(600)).toBe(8);
  });
});

describe("tooltip formatting", () => {
  it("formats clocks and rates per language", () => {
    expect(formatClock(at("13:05"), "Europe/Paris", "en")).toBe("15:05");
    expect(formatClock(at("13:05"), "Europe/Paris", "fr")).toBe("15h05");
    expect(formatClock(at("22:00"), "Europe/Paris", "en")).toBe("00:00");
    expect(formatRate(1.2, "fr")).toBe("1,2 mm/h");
    expect(formatRate(0.4296, "en")).toBe("0.43 mm/h");
    expect(formatRate(0, "en")).toBe("0 mm/h");
  });

  it("joins the range and the rate, or says there is no data", () => {
    const from = at("13:05");
    const to = at("13:10");
    expect(segmentTooltip(from, to, 1.2, "Europe/Paris", "en", "no data")).toBe(
      "15:05-15:10 · 1.2 mm/h",
    );
    expect(segmentTooltip(from, to, 1.2, "Europe/Paris", "fr", "pas de données")).toBe(
      "15h05-15h10 · 1,2 mm/h",
    );
    expect(segmentTooltip(from, to, null, "Europe/Paris", "fr", "pas de données")).toBe(
      "15h05-15h10 · pas de données",
    );
  });

  it("falls back to the browser zone on an unknown zone name", () => {
    expect(() => formatClock(at("13:05"), "Not/AZone", "en")).not.toThrow();
  });
});
