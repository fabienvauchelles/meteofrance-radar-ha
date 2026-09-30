// Playback clock: advances through the timeline steps on animation frames and waits
// while the layers of the current step are still being fetched or decoded.

import { type Step, weightAt, wrapIndex } from "./timeline";
import type { CardSeams } from "./types";

export interface PlaybackHooks {
  steps(): readonly Step[];
  /** Draw a step at a fade weight; false when its layers are not decoded yet. */
  render(stepIndex: number, weight: number): boolean;
  /** Fetch and decode the layers of a step. */
  ensure(stepIndex: number): Promise<void>;
  /** Called whenever playing, waiting or the step changes. */
  changed(): void;
}

type Clock = Pick<CardSeams, "now" | "requestFrame" | "cancelFrame">;

export class Playback {
  stepIndex = 0;
  playing = false;
  waiting = false;
  private elapsed = 0;
  private resumeAfterScrub = false;
  private lastTick: number | null = null;
  private handle: number | null = null;

  constructor(
    private readonly hooks: PlaybackHooks,
    private readonly clock: Clock,
  ) {}

  play(): void {
    if (this.playing || this.hooks.steps().length === 0) return;
    this.playing = true;
    this.lastTick = null;
    this.schedule();
    this.hooks.changed();
  }

  pause(): void {
    if (this.handle !== null) this.clock.cancelFrame(this.handle);
    this.handle = null;
    if (!this.playing) return;
    this.playing = false;
    this.hooks.changed();
  }

  toggle(): void {
    if (this.playing) this.pause();
    else this.play();
  }

  /** Put the position at the start of a step, without drawing. */
  moveTo(stepIndex: number): void {
    this.stepIndex = stepIndex;
    this.elapsed = 0;
    this.lastTick = null;
  }

  /** Move to a step and draw it as soon as its layers are ready. */
  async seek(stepIndex: number): Promise<void> {
    this.moveTo(stepIndex);
    this.hooks.changed();
    if (this.hooks.render(stepIndex, 0)) return;
    await this.hooks.ensure(stepIndex);
    if (this.stepIndex === stepIndex && this.elapsed === 0) this.hooks.render(stepIndex, 0);
  }

  stepBy(delta: number): Promise<void> {
    this.pause();
    return this.seek(wrapIndex(this.stepIndex, delta, this.hooks.steps().length));
  }

  /** Follow the time slider: playback pauses while it is dragged. */
  scrub(stepIndex: number): Promise<void> {
    if (this.playing) {
      this.resumeAfterScrub = true;
      this.pause();
    }
    return this.seek(stepIndex);
  }

  /** The slider was released: resume when the drag paused playback. */
  scrubEnd(): void {
    if (this.resumeAfterScrub) this.play();
    this.resumeAfterScrub = false;
  }

  private schedule(): void {
    this.handle = this.clock.requestFrame(() => this.tick());
  }

  private tick(): void {
    this.handle = null;
    if (!this.playing || this.hooks.steps().length === 0) return;
    const now = this.clock.now();
    const delta = this.lastTick === null ? 0 : now - this.lastTick;
    this.lastTick = now;
    if (!this.waiting) this.advance(delta);
    this.schedule();
  }

  private advance(delta: number): void {
    const steps = this.hooks.steps();
    const before = this.stepIndex;
    this.stepIndex = Math.min(this.stepIndex, steps.length - 1);
    this.elapsed += delta;
    let step = steps[this.stepIndex];
    while (step && this.elapsed >= step.durationMs) {
      this.elapsed -= step.durationMs;
      this.stepIndex = wrapIndex(this.stepIndex, 1, steps.length);
      step = steps[this.stepIndex];
    }
    if (!step) return;
    if (this.stepIndex !== before) this.hooks.changed();
    if (this.hooks.render(this.stepIndex, weightAt(step, this.elapsed))) return;
    this.wait(this.stepIndex);
  }

  private wait(stepIndex: number): void {
    this.waiting = true;
    this.hooks.changed();
    this.hooks
      .ensure(stepIndex)
      .catch(() => {
        // A layer that cannot load is skipped rather than stalling the loop.
        if (this.stepIndex === stepIndex) {
          this.moveTo(wrapIndex(stepIndex, 1, this.hooks.steps().length));
        }
      })
      .finally(() => {
        this.waiting = false;
        this.lastTick = null;
        this.hooks.changed();
      });
  }
}
