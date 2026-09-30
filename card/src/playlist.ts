// Pure playlist: the observed radar frames, then the frames of the latest nowcast run.
// The last observed frame is "now"; forecast frames always crossfade from the one
// before them, including the step from the radar into the forecast.

import type { FramesResponse } from "./types";

export interface PlayFrame {
  time: string;
  url: string;
  gap_before_min: number;
  forecast: boolean;
  /** Minutes after "now" for a forecast frame, null for an observed one. */
  lead_min: number | null;
}

export interface Playlist {
  frames: PlayFrame[];
  /** Index of the last observed frame, -1 when there is none. */
  nowIndex: number;
  /** Number of forecast frames at the end of `frames`. */
  forecastCount: number;
}

export const EMPTY_PLAYLIST: Playlist = { frames: [], nowIndex: -1, forecastCount: 0 };

export function buildPlaylist(data: FramesResponse | null, showForecast: boolean): Playlist {
  if (!data) return EMPTY_PLAYLIST;
  const observed: PlayFrame[] = data.frames.map((frame) => ({
    time: frame.time,
    url: frame.url,
    gap_before_min: frame.gap_before_min,
    forecast: false,
    lead_min: null,
  }));
  const last = observed[observed.length - 1];
  const after = last ? Date.parse(last.time) : Number.NEGATIVE_INFINITY;
  const forecast: PlayFrame[] = showForecast
    ? (data.forecast?.frames ?? [])
        .filter((frame) => Date.parse(frame.time) > after)
        .map((frame) => ({
          time: frame.time,
          url: frame.url,
          gap_before_min: 0,
          forecast: true,
          lead_min: frame.lead_min,
        }))
    : [];
  return {
    frames: [...observed, ...forecast],
    nowIndex: observed.length - 1,
    forecastCount: forecast.length,
  };
}

/** Position of the "now" marker as a percentage of the slider, null when nothing follows it. */
export function nowPercent(playlist: Playlist): number | null {
  const count = playlist.frames.length;
  if (playlist.forecastCount === 0 || playlist.nowIndex < 0 || count < 2) return null;
  return (playlist.nowIndex / (count - 1)) * 100;
}

/**
 * Frame to show after a load: the kept time when there is one, the first frame when
 * playback starts, else the "now" frame (the first forecast frame when nothing was observed).
 */
export function restingIndex(
  playlist: Playlist,
  keepIndex: number | null,
  autoplay: boolean,
): number {
  if (keepIndex !== null) return keepIndex;
  if (autoplay) return 0;
  return Math.max(0, playlist.nowIndex);
}
