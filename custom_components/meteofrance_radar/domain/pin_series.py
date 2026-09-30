"""Rain bar at the home pin: its time window, its segments and how sources are stitched.

The bar shows the past 3 hours observed by the radar, then forecasts up to midnight
Europe/Paris but never less than 6 hours ahead. Each forecast source starts where the
previous available one ends: radar, then PIAF, then AROME-PI, then AROME.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from typing import Final
from zoneinfo import ZoneInfo

import numpy as np

from .palette import NODATA_INDEX, classify

BAR_TIME_ZONE: Final = "Europe/Paris"
PAST_SPAN: Final = timedelta(hours=3)
MIN_AHEAD: Final = timedelta(hours=6)
PIAF_FINE_LEAD_MAX_MIN: Final = 60
PIAF_FINE_STEP: Final = timedelta(minutes=5)
PIAF_COARSE_STEP: Final = timedelta(minutes=15)


class SegmentSource(StrEnum):
    """Where a segment's value comes from."""

    RADAR = "radar"
    PIAF = "piaf"
    AROMEPI = "aromepi"
    AROME = "arome"


@dataclass(frozen=True)
class Segment:
    """Rain rate over [start, end); mm_h None means no data, cls is the palette index."""

    source: SegmentSource
    start: datetime
    end: datetime
    mm_h: float | None
    cls: int


@dataclass(frozen=True)
class BarWindow:
    """Time span the bar covers, in UTC."""

    start: datetime
    end: datetime


def bar_window(now: datetime) -> BarWindow:
    """Window of the bar: 3 hours back, forward to the later of next Paris midnight and +6 h.

    The midnight is the first one strictly after `now`, computed in local time so the
    daylight saving change days come out right.
    """
    if now.tzinfo is None:
        raise ValueError("bar_window needs a timezone-aware time")
    now_utc = now.astimezone(UTC)
    local = now_utc.astimezone(ZoneInfo(BAR_TIME_ZONE))
    midnight = datetime.combine(
        local.date() + timedelta(days=1), time(0), tzinfo=ZoneInfo(BAR_TIME_ZONE)
    ).astimezone(UTC)
    return BarWindow(start=now_utc - PAST_SPAN, end=max(midnight, now_utc + MIN_AHEAD))


def class_of(mm_h: float | None) -> int:
    """Palette index of one rate: 0 dry, 1-10 rain classes, 11 for None or NaN."""
    if mm_h is None or math.isnan(mm_h):
        return NODATA_INDEX
    return int(classify(np.array([mm_h], dtype=np.float32))[0])


def piaf_segment_length(lead_min: int) -> timedelta:
    """Span a PIAF step stands for: 5 minutes up to +60, 15 minutes beyond."""
    return PIAF_FINE_STEP if lead_min <= PIAF_FINE_LEAD_MAX_MIN else PIAF_COARSE_STEP


def segments_ending_at(
    source: SegmentSource,
    values: Sequence[tuple[datetime, float | None]],
    length: timedelta | Callable[[datetime], timedelta],
) -> list[Segment]:
    """Segments [valid - length, valid) for each (valid, mm/h) value, ascending.

    `length` is fixed, or a function of the valid time. NaN is stored as None (no data).
    """
    segments = []
    for valid, mm_h in sorted(values, key=lambda item: item[0]):
        span = length(valid) if callable(length) else length
        rate = None if mm_h is None or math.isnan(mm_h) else mm_h
        segments.append(Segment(source, valid - span, valid, rate, class_of(rate)))
    return segments


def _after_cursor(segments: Sequence[Segment], cursor: datetime) -> list[Segment]:
    kept = []
    for segment in sorted(segments, key=lambda s: s.start):
        if segment.end <= cursor:
            continue
        kept.append(replace(segment, start=cursor) if segment.start < cursor else segment)
    return kept


def _clip(segment: Segment, window: BarWindow) -> Segment | None:
    start = max(segment.start, window.start)
    end = min(segment.end, window.end)
    if start >= end:
        return None
    return replace(segment, start=start, end=end)


def stitch(
    radar: Sequence[Segment],
    forecasts: Sequence[Sequence[Segment]],
    window: BarWindow,
) -> list[Segment]:
    """Join radar and forecast segments into one ascending, non-overlapping list.

    Radar segments are kept as they are, gaps included. Each forecast source, in the
    order given, drops what ends at or before the cursor, clips its first overlapping
    segment to start there, and moves the cursor to its own last end. Everything is then
    clipped to the window and empty segments dropped.
    """
    ordered_radar = sorted(radar, key=lambda s: s.start)
    cursor = max((s.end for s in ordered_radar), default=window.start)
    merged = list(ordered_radar)
    for source_segments in forecasts:
        kept = _after_cursor(source_segments, cursor)
        if kept:
            merged.extend(kept)
            cursor = kept[-1].end
    clipped = (_clip(segment, window) for segment in merged)
    return [segment for segment in clipped if segment is not None]
