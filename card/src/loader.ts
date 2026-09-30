// Layer loader: compressed PNG blobs in an LRU keyed by URL (layer URLs are immutable,
// so the cache survives a frame list refresh), fetched with bounded concurrency, and a
// small window of decoded ImageBitmaps around the playback position.

export const MAX_BLOBS = 300;
export const MAX_CONCURRENT_FETCHES = 4;
/** Frames kept decoded after the current one. */
export const DECODED_AHEAD = 3;
/** Frames whose blobs are fetched ahead of the decoded window. */
export const PREFETCH_AHEAD = 8;
/** A layer that failed is not requested again for this long (each pass would log a 500). */
export const RETRY_FAILED_MS = 5 * 60_000;

/** URLs `offset` from `first` to `last` (inclusive) after `index`, wrapping, never repeating. */
function around(urls: readonly string[], index: number, first: number, last: number): string[] {
  const picked: string[] = [];
  for (let offset = first; offset <= last && offset < urls.length; offset += 1) {
    const url = urls[(index + offset) % urls.length];
    if (url !== undefined) picked.push(url);
  }
  return picked;
}

export interface LoaderDeps {
  fetchBlob(url: string): Promise<Blob>;
  decode(blob: Blob): Promise<ImageBitmap>;
}

interface Job {
  url: string;
  resolve(blob: Blob): void;
  reject(error: unknown): void;
}

export class LayerLoader {
  private readonly blobs = new Map<string, Blob>();
  private readonly pending = new Map<string, Promise<Blob>>();
  private readonly queue: Job[] = [];
  private active = 0;
  private readonly bitmaps = new Map<string, ImageBitmap>();
  private readonly decoding = new Map<string, Promise<ImageBitmap>>();
  private wanted = new Set<string>();
  private windowKey = "";
  private closed = false;
  private readonly failed = new Map<string, { at: number; error: unknown }>();

  constructor(private readonly deps: LoaderDeps) {}

  /** The compressed layer, from the LRU or fetched (urgent requests jump the queue). */
  blob(url: string, urgent = true): Promise<Blob> {
    const cached = this.blobs.get(url);
    if (cached) {
      this.blobs.delete(url);
      this.blobs.set(url, cached);
      return Promise.resolve(cached);
    }
    const failure = this.failed.get(url);
    if (failure && Date.now() - failure.at < RETRY_FAILED_MS) return Promise.reject(failure.error);
    this.failed.delete(url);
    const inflight = this.pending.get(url);
    if (inflight) {
      if (urgent) this.promote(url);
      return inflight;
    }
    const promise = new Promise<Blob>((resolve, reject) => {
      const job = { url, resolve, reject };
      if (urgent) this.queue.unshift(job);
      else this.queue.push(job);
    });
    this.pending.set(url, promise);
    this.pump();
    return promise;
  }

  /** Warm the blob cache for upcoming layers without blocking anything. */
  prefetch(urls: readonly string[]): void {
    for (const url of urls) this.blob(url, false).catch(() => {});
  }

  /** Keep exactly these layers decoded; bitmaps outside the window are released. */
  setWindow(urls: readonly string[]): void {
    this.wanted = new Set(urls);
    for (const [url, bitmap] of this.bitmaps) {
      if (this.wanted.has(url)) continue;
      bitmap.close();
      this.bitmaps.delete(url);
    }
    for (const url of urls) this.decode(url).catch(() => {});
  }

  /**
   * Follow the playback position in `urls` (the frame list): decode the current frame
   * and the next DECODED_AHEAD, fetch the PREFETCH_AHEAD blobs after them.
   */
  focus(urls: readonly string[], index: number): void {
    const decoded = around(urls, index, 0, DECODED_AHEAD);
    const key = decoded.join("|");
    if (key === this.windowKey) return;
    this.windowKey = key;
    this.setWindow(decoded);
    this.prefetch(around(urls, index, DECODED_AHEAD + 1, DECODED_AHEAD + PREFETCH_AHEAD));
  }

  /** Resolve once every layer is decoded; rejects when one cannot be fetched or decoded. */
  async ensure(urls: readonly string[]): Promise<void> {
    await Promise.all(urls.map((url) => this.decode(url)));
  }

  /** The decoded layer when it is ready, else null. */
  bitmap(url: string): ImageBitmap | null {
    return this.bitmaps.get(url) ?? null;
  }

  close(): void {
    this.closed = true;
    for (const job of this.queue) job.reject(new Error("loader closed"));
    this.queue.length = 0;
    for (const bitmap of this.bitmaps.values()) bitmap.close();
    this.bitmaps.clear();
  }

  private decode(url: string): Promise<ImageBitmap> {
    const ready = this.bitmaps.get(url);
    if (ready) return Promise.resolve(ready);
    const inflight = this.decoding.get(url);
    if (inflight) return inflight;
    const promise = this.blob(url)
      .then((blob) => this.deps.decode(blob))
      .then((bitmap) => {
        // A layer that left the window while decoding is released straight away.
        if (this.closed || !this.wanted.has(url)) bitmap.close();
        else this.bitmaps.set(url, bitmap);
        return bitmap;
      })
      .finally(() => this.decoding.delete(url));
    this.decoding.set(url, promise);
    return promise;
  }

  private promote(url: string): void {
    const at = this.queue.findIndex((job) => job.url === url);
    if (at <= 0) return;
    const [job] = this.queue.splice(at, 1);
    if (job) this.queue.unshift(job);
  }

  private pump(): void {
    while (!this.closed && this.active < MAX_CONCURRENT_FETCHES) {
      const job = this.queue.shift();
      if (!job) return;
      this.active += 1;
      this.deps
        .fetchBlob(job.url)
        .then(
          (blob) => {
            this.remember(job.url, blob);
            job.resolve(blob);
          },
          (error: unknown) => {
            this.failed.set(job.url, { at: Date.now(), error });
            job.reject(error);
          },
        )
        .finally(() => {
          this.pending.delete(job.url);
          this.active -= 1;
          this.pump();
        });
    }
  }

  private remember(url: string, blob: Blob): void {
    this.blobs.set(url, blob);
    for (const oldest of this.blobs.keys()) {
      if (this.blobs.size <= MAX_BLOBS) return;
      this.blobs.delete(oldest);
    }
  }
}
