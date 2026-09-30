"""The pin_series answer: one rain bar at the home, observed then forecast.

Pure: the view reads the radar values in the executor and hands them over with the
committed forecasts; this module turns them into stitched segments.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any, Final

from ..const import ATTRIBUTION_RADAR
from ..domain.forecast import (
    ForecastProduct,
    ForecastState,
    PiafRun,
    PinSeries,
    ProductStatus,
    same_pin,
)
from ..domain.palette import legend
from ..domain.pin_series import (
    Segment,
    SegmentSource,
    bar_window,
    piaf_segment_length,
    segments_ending_at,
    stitch,
)
from ..domain.slots import SLOT, format_iso
from .forecast import FRESH_RADAR
from .frames import HomeLocation

AROMEPI_STEP: Final = timedelta(minutes=15)
AROME_STEP: Final = timedelta(hours=1)
MM_H_DECIMALS: Final = 2
RADAR_OK: Final = "ok"
RADAR_STALE: Final = "stale"
RADAR_PENDING: Final = "pending"


def radar_query_range(now: datetime, latest: datetime | None) -> tuple[datetime, datetime] | None:
    """[start, end) of the radar slots the bar needs, None on an empty archive.

    A slot covers the five minutes ending at it, so the first useful slot ends just
    after the window start.
    """
    if latest is None:
        return None
    return bar_window(now).start - SLOT, latest + SLOT


def _piaf_segments(piaf: PiafRun | None, pin: tuple[float, float]) -> list[Segment]:
    if piaf is None or not same_pin(piaf.pin, pin):
        return []
    leads = {step.valid: step.lead_min for step in piaf.steps}
    values = [(s.valid, s.pin_mm_h) for s in piaf.steps if s.pin_mm_h is not None]
    return segments_ending_at(
        SegmentSource.PIAF,
        values,
        lambda valid: piaf_segment_length(leads[valid]),
    )


def _pin_segments(
    series: PinSeries | None,
    pin: tuple[float, float],
    source: SegmentSource,
    length: timedelta,
) -> list[Segment]:
    if series is None or not same_pin((series.lon, series.lat), pin):
        return []
    values: list[tuple[datetime, float | None]] = [(v.valid, v.mm_h) for v in series.values]
    return segments_ending_at(source, values, length)


def _segment_payload(segment: Segment) -> dict[str, Any]:
    return {
        "source": segment.source.value,
        "start": format_iso(segment.start),
        "end": format_iso(segment.end),
        "mm_h": None if segment.mm_h is None else round(segment.mm_h, MM_H_DECIMALS),
        "class": segment.cls,
    }


def _radar_status(now: datetime, latest: datetime | None) -> str:
    if latest is None:
        return RADAR_PENDING
    return RADAR_OK if now - latest <= FRESH_RADAR else RADAR_STALE


def _source_payload(
    product: ForecastProduct, state: ForecastState | None, run: datetime | None
) -> dict[str, Any]:
    product_state = None if state is None else state.of(product)
    status = ProductStatus.PENDING if product_state is None else product_state.status
    if run is None and product_state is not None:
        run = product_state.run
    return {"status": status.value, "run": None if run is None else format_iso(run)}


def build_pin_series_payload(
    *,
    now: datetime,
    version: str,
    home: HomeLocation | None,
    radar: Sequence[tuple[datetime, float | None]],
    latest: datetime | None,
    piaf: PiafRun | None,
    aromepi: PinSeries | None,
    arome: PinSeries | None,
    state: ForecastState | None,
) -> dict[str, Any]:
    """JSON-ready answer of GET /api/meteofrance_radar/pin_series.

    Args:
        now: Current aware time; sets the bar window.
        version: Integration version.
        home: HA home location, None when unset (the bar then has no segments).
        radar: (slot, mm/h or None) at the home cell, ascending; each value covers the
            five minutes ending at its slot.
        latest: Latest stored radar slot, None on an empty archive.
        piaf: The committed PIAF run; its pin values count only if read at the home.
        aromepi: Saved AROME-PI pin series; ignored when read at another point.
        arome: Saved AROME pin series; ignored when read at another point.
        state: Forecast product states, None before the first forecast tick.

    Returns:
        {version, now, window, located, legend, segments, sources, attribution}, the
        segments ascending and non-overlapping: radar, then PIAF, AROME-PI and AROME,
        each forecast source starting where the previous available one ends.
    """
    window = bar_window(now)
    segments: list[Segment] = []
    if home is not None:
        pin = (home.lon, home.lat)
        radar_segments = segments_ending_at(SegmentSource.RADAR, radar, SLOT)
        forecasts = [
            _piaf_segments(piaf, pin),
            _pin_segments(aromepi, pin, SegmentSource.AROMEPI, AROMEPI_STEP),
            _pin_segments(arome, pin, SegmentSource.AROME, AROME_STEP),
        ]
        segments = stitch(radar_segments, forecasts, window)
    return {
        "version": version,
        "now": format_iso(now),
        "window": {"start": format_iso(window.start), "end": format_iso(window.end)},
        "located": home is not None,
        "legend": legend(),
        "segments": [_segment_payload(segment) for segment in segments],
        "sources": {
            "radar": {
                "status": _radar_status(now, latest),
                "latest": None if latest is None else format_iso(latest),
            },
            "piaf": _source_payload(
                ForecastProduct.PIAF, state, None if piaf is None else piaf.run
            ),
            "aromepi": _source_payload(
                ForecastProduct.AROMEPI, state, None if aromepi is None else aromepi.run
            ),
            "arome": _source_payload(
                ForecastProduct.AROME, state, None if arome is None else arome.run
            ),
        },
        "attribution": ATTRIBUTION_RADAR,
    }
