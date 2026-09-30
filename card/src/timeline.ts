// Pure playback timeline. One step per stored frame, all of the same duration, so
// missing slots are skipped. A step fades into the next frame over its last
// crossfade_ms, except when that frame follows a gap, where it cuts. The last step
// cuts back to the first one when playback loops.

export interface Timing {
  frameMs: number;
  crossfadeMs: number;
}

export interface Step {
  /** Frame shown when the step starts. */
  frame: number;
  /** Frame faded in at the end of the step, null when the step ends on a cut. */
  next: number | null;
  durationMs: number;
  fadeMs: number;
}

export interface GapInfo {
  gap_before_min: number;
}

export function buildSteps(frames: readonly GapInfo[], timing: Timing): Step[] {
  const durationMs = Math.max(1, timing.frameMs);
  const fadeMs = Math.max(0, Math.min(timing.crossfadeMs, durationMs));
  return frames.map((_, index) => {
    const following = frames[index + 1];
    const fades = following !== undefined && following.gap_before_min <= 0 && fadeMs > 0;
    return {
      frame: index,
      next: fades ? index + 1 : null,
      durationMs,
      fadeMs: fades ? fadeMs : 0,
    };
  });
}

/** Weight of the next frame after `elapsedMs` in the step, from 0 (none) to 1. */
export function weightAt(step: Step, elapsedMs: number): number {
  if (step.next === null || step.fadeMs <= 0) return 0;
  const fadeStart = step.durationMs - step.fadeMs;
  if (elapsedMs <= fadeStart) return 0;
  return Math.min(1, (elapsedMs - fadeStart) / step.fadeMs);
}

/** Frame whose time the title shows: the current one, then the next from mid-fade. */
export function titleFrame(step: Step, weight: number): number {
  return step.next !== null && weight >= 0.5 ? step.next : step.frame;
}

/** Move `delta` steps from `index`, wrapping around both ends. */
export function wrapIndex(index: number, delta: number, count: number): number {
  if (count <= 0) return 0;
  return (((index + delta) % count) + count) % count;
}

/**
 * Index of the frame to keep after the list changed: the same time when it is still
 * there, else the latest frame before it, else the first frame.
 */
export function findFrame(times: readonly string[], time: string): number {
  const target = Date.parse(time);
  let best = 0;
  for (let index = 0; index < times.length; index += 1) {
    const value = Date.parse(times[index] ?? "");
    if (value > target) break;
    best = index;
  }
  return best;
}

/** Layer URLs of a step: the frame shown, then the frame faded in (or null). */
export function stepUrls(
  steps: readonly Step[],
  urls: readonly string[],
  stepIndex: number,
): [string, string | null] | null {
  const step = steps[stepIndex];
  const first = step ? urls[step.frame] : undefined;
  if (!step || first === undefined) return null;
  return [first, step.next === null ? null : (urls[step.next] ?? null)];
}
