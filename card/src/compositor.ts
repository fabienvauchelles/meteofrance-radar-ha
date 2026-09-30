// Canvas compositor, ported from the radarviz player: two offscreen composites
// (basemap + layer A, basemap + layer B) blended on the visible canvas as A, then B
// with globalAlpha = weight. A is opaque, so the result is (1 - w) * A + w * B.

export interface Layer {
  key: string;
  bitmap: CanvasImageSource;
}

interface Slot {
  key: string | null;
  canvas: HTMLCanvasElement;
}

type ContextFactory = (canvas: HTMLCanvasElement) => CanvasRenderingContext2D | null;

export class Compositor {
  private readonly context: CanvasRenderingContext2D | null;
  private readonly slots: [Slot, Slot];
  private basemap: CanvasImageSource | null = null;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    readonly width: number,
    readonly height: number,
    private readonly contextOf: ContextFactory,
  ) {
    canvas.width = width;
    canvas.height = height;
    this.context = contextOf(canvas);
    this.slots = [this.makeSlot(), this.makeSlot()];
  }

  /** Whether this compositor still draws on `canvas` with the given size. */
  matches(canvas: HTMLCanvasElement, width: number, height: number): boolean {
    return this.canvas === canvas && this.width === width && this.height === height;
  }

  setBasemap(image: CanvasImageSource | null): void {
    this.basemap = image;
    this.reset();
  }

  reset(): void {
    for (const slot of this.slots) slot.key = null;
  }

  /** Draw the basemap alone, for an empty period. */
  drawBasemap(): void {
    const context = this.context;
    if (!context) return;
    context.globalAlpha = 1;
    context.clearRect(0, 0, this.width, this.height);
    if (this.basemap) context.drawImage(this.basemap, 0, 0, this.width, this.height);
  }

  /** Draw layer A blended with layer B at `weight` (B's share, 0 to 1). */
  draw(a: Layer, b: Layer | null, weight: number): void {
    const context = this.context;
    if (!context) return;
    const compositeA = this.composite(a, b?.key ?? null);
    context.globalAlpha = 1;
    // Without a basemap the composites are transparent where it is dry, so the
    // previous frame would show through.
    context.clearRect(0, 0, this.width, this.height);
    context.drawImage(compositeA, 0, 0);
    if (b === null || weight <= 0) return;
    const compositeB = this.composite(b, a.key);
    context.globalAlpha = Math.min(1, weight);
    context.drawImage(compositeB, 0, 0);
    context.globalAlpha = 1;
  }

  private makeSlot(): Slot {
    const canvas = document.createElement("canvas");
    canvas.width = this.width;
    canvas.height = this.height;
    return { key: null, canvas };
  }

  /** Composite of a layer, reusing a cached one and never overwriting `keep`. */
  private composite(layer: Layer, keep: string | null): HTMLCanvasElement {
    const hit = this.slots.find((slot) => slot.key === layer.key);
    if (hit) return hit.canvas;
    const target = this.slots.find((slot) => slot.key !== keep) ?? this.slots[0];
    const context = this.contextOf(target.canvas);
    if (context) {
      context.globalAlpha = 1;
      context.clearRect(0, 0, this.width, this.height);
      if (this.basemap) context.drawImage(this.basemap, 0, 0, this.width, this.height);
      context.drawImage(layer.bitmap, 0, 0, this.width, this.height);
    }
    target.key = layer.key;
    return target.canvas;
  }
}
