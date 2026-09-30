import { describe, expect, it } from "vitest";
import { buildSteps, findFrame, stepUrls, titleFrame, weightAt, wrapIndex } from "../src/timeline";

const frames = (gaps: number[]) => gaps.map((gap_before_min) => ({ gap_before_min }));

describe("buildSteps", () => {
  it("gives every frame the same duration and fades into the next one", () => {
    const steps = buildSteps(frames([0, 0, 0]), { frameMs: 500, crossfadeMs: 300 });
    expect(steps).toEqual([
      { frame: 0, next: 1, durationMs: 500, fadeMs: 300 },
      { frame: 1, next: 2, durationMs: 500, fadeMs: 300 },
      { frame: 2, next: null, durationMs: 500, fadeMs: 0 },
    ]);
  });

  it("cuts instead of fading into a frame that follows a gap", () => {
    const steps = buildSteps(frames([0, 0, 25, 0]), { frameMs: 400, crossfadeMs: 200 });
    expect(steps.map((step) => step.next)).toEqual([1, null, 3, null]);
    expect(steps[1]?.fadeMs).toBe(0);
    expect(steps[1]?.durationMs).toBe(400);
  });

  it("never fades longer than the frame and cuts when the fade is zero", () => {
    expect(buildSteps(frames([0, 0]), { frameMs: 200, crossfadeMs: 900 })[0]?.fadeMs).toBe(200);
    expect(buildSteps(frames([0, 0]), { frameMs: 200, crossfadeMs: 0 })[0]?.next).toBeNull();
    expect(buildSteps([], { frameMs: 500, crossfadeMs: 300 })).toEqual([]);
  });
});

describe("weights and the title frame", () => {
  const [fading, last] = buildSteps(frames([0, 0]), { frameMs: 500, crossfadeMs: 300 });

  it("holds the frame, then ramps the next one in over the fade", () => {
    if (!fading || !last) throw new Error("steps missing");
    expect(weightAt(fading, 0)).toBe(0);
    expect(weightAt(fading, 200)).toBe(0);
    expect(weightAt(fading, 350)).toBeCloseTo(0.5);
    expect(weightAt(fading, 500)).toBe(1);
    expect(weightAt(last, 450)).toBe(0);
  });

  it("switches the title half way through the fade", () => {
    if (!fading || !last) throw new Error("steps missing");
    expect(titleFrame(fading, 0.49)).toBe(0);
    expect(titleFrame(fading, 0.5)).toBe(1);
    expect(titleFrame(last, 1)).toBe(1);
  });

  it("stays on the frame through a cut", () => {
    const [cut] = buildSteps(frames([0, 30]), { frameMs: 500, crossfadeMs: 300 });
    if (!cut) throw new Error("step missing");
    expect(weightAt(cut, 499)).toBe(0);
    expect(titleFrame(cut, weightAt(cut, 499))).toBe(0);
  });
});

describe("navigation helpers", () => {
  it("wraps indexes both ways", () => {
    expect(wrapIndex(0, -1, 5)).toBe(4);
    expect(wrapIndex(4, 1, 5)).toBe(0);
    expect(wrapIndex(2, 0, 0)).toBe(0);
  });

  it("finds the same time, else the latest one before it", () => {
    const times = ["2026-09-30T10:00:00Z", "2026-09-30T10:05:00Z", "2026-09-30T10:15:00Z"];
    expect(findFrame(times, "2026-09-30T10:05:00Z")).toBe(1);
    expect(findFrame(times, "2026-09-30T10:10:00Z")).toBe(1);
    expect(findFrame(times, "2026-09-30T09:00:00Z")).toBe(0);
  });

  it("names the layers a step needs", () => {
    const steps = buildSteps(frames([0, 0]), { frameMs: 500, crossfadeMs: 300 });
    expect(stepUrls(steps, ["a", "b"], 0)).toEqual(["a", "b"]);
    expect(stepUrls(steps, ["a", "b"], 1)).toEqual(["b", null]);
    expect(stepUrls(steps, ["a", "b"], 2)).toBeNull();
  });
});
