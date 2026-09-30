"""The frames API answer: what the card needs to play a period, as a JSON-ready dict.

Pure: it works on the in-memory frame index and the clock value it is given, so the
view can call it in the event loop without touching the disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from ..const import (
    ATTRIBUTION_BASEMAP,
    ATTRIBUTION_RADAR,
    BASEMAP_FILENAME,
    URL_LAYERS,
    URL_STATIC_BASE,
)
from ..domain.grid import TargetGrid
from ..domain.models import FrameEntry
from ..domain.palette import legend
from ..domain.periods import Period, parse_period_name, resolve_period
from ..domain.slots import format_iso, format_slot
from ..domain.tiers import count_missing, gaps_before, tier_of

LAYER_SUFFIX: Final = ".png"


@dataclass(frozen=True)
class HomeLocation:
    """WGS84 position of the Home Assistant home."""

    lat: float
    lon: float


def layer_url(style: str, slot: datetime) -> str:
    """Immutable URL of the rendered layer of a slot for a style."""
    return URL_LAYERS.format(style=style, name=f"{format_slot(slot)}{LAYER_SUFFIX}")


def basemap_url(version: str) -> str:
    """Basemap URL, versioned so a new release busts the browser cache."""
    return f"{URL_STATIC_BASE}/{BASEMAP_FILENAME}?v={version}"


def pin_payload(grid: TargetGrid, home: HomeLocation | None) -> dict[str, Any] | None:
    """Basemap pixel of the home, with an inside flag; None when HA has no location."""
    if home is None:
        return None
    x, y = grid.lonlat_to_pixel(home.lon, home.lat)
    return {"x": round(x, 1), "y": round(y, 1), "inside": grid.contains_pixel(x, y)}


def _period_payload(period: Period | None) -> dict[str, str] | None:
    if period is None:
        return None
    return {
        "name": period.name.value,
        "from": format_iso(period.start),
        "to": format_iso(period.end),
    }


def _frames_payload(
    entries: Sequence[FrameEntry], period: Period | None, now: datetime, style: str
) -> tuple[list[dict[str, Any]], int]:
    """Frames of the period with their tier and jumped gap, plus the missing bucket count."""
    if period is None:
        return [], 0
    slots = [e.slot for e in entries if period.start <= e.slot < period.end]
    gaps = gaps_before(slots, now)
    frames = [
        {
            "time": format_iso(slot),
            "tier": tier_of(slot, now).value,
            "gap_before_min": gap,
            "url": layer_url(style, slot),
        }
        for slot, gap in zip(slots, gaps, strict=True)
    ]
    return frames, count_missing(slots, period.start, period.end, now)


def build_frames_payload(
    *,
    period_name: str | None,
    entries: Sequence[FrameEntry],
    now: datetime,
    grid: TargetGrid,
    style: str,
    version: str,
    home: HomeLocation | None,
    forecast: dict[str, Any] | None,
) -> dict[str, Any]:
    """JSON-ready answer of GET /api/meteofrance_radar/frames.

    Args:
        period_name: Query value ("3h", "24h", "7d", "30d", "all"); None means "3h".
        entries: Every stored frame, ascending by slot.
        now: Current aware time, which sets the tier of each frame.
        grid: Target grid shared by the basemap and the layers.
        style: Current layer style id.
        version: Integration version, appended to the basemap URL.
        home: HA home location, None when unset.
        forecast: The "forecast" object (see ``http.forecast``), None when the
            forecast runtime is not available.

    Returns:
        The payload described in the design (section 7, and 5.1 of the 0.2.0 design).
        On an empty archive, frames is empty and period, latest and oldest are None.

    Raises:
        PeriodError: period_name is not a known period.
    """
    name = parse_period_name(period_name)
    oldest = entries[0].slot if entries else None
    latest = entries[-1].slot if entries else None
    period = resolve_period(name, oldest, latest)
    frames, missing = _frames_payload(entries, period, now, style)
    return {
        "version": version,
        "style": style,
        "grid": grid.as_dict(),
        "basemap": basemap_url(version),
        "pin": pin_payload(grid, home),
        "attribution": {"radar": ATTRIBUTION_RADAR, "basemap": ATTRIBUTION_BASEMAP},
        "legend": legend(),
        "period": _period_payload(period),
        "latest": None if latest is None else format_iso(latest),
        "oldest": None if oldest is None else format_iso(oldest),
        "frames": frames,
        "missing": missing,
        "forecast": forecast,
    }
