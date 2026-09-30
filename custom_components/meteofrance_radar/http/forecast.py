"""The "forecast" part of the frames answer: PIAF steps the card plays after "now".

Pure: it works on the committed PIAF run and the clock value it is given.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Final

from ..const import URL_FORECAST_LAYERS
from ..domain.forecast import ForecastProduct, PiafRun, ProductState, ProductStatus
from ..domain.slots import floor_slot, format_iso, format_slot

LAYER_SUFFIX: Final = ".png"
# The latest radar slot stands for "now" while it is at most this old.
FRESH_RADAR: Final = timedelta(minutes=15)
SECONDS_PER_MINUTE: Final = 60


def now_marker(latest: datetime | None, now: datetime) -> datetime:
    """Time the slider marks as "now".

    The latest stored radar slot while it is fresh, else the clock floored to a slot,
    so a stalled collector never shifts the forecast leads.
    """
    if latest is not None and now - latest <= FRESH_RADAR:
        return latest
    return floor_slot(now)


def forecast_layer_url(style: str, run: datetime, valid: datetime) -> str:
    """Immutable URL of the forecast layer of a PIAF step."""
    return URL_FORECAST_LAYERS.format(
        style=style, run=format_slot(run), name=f"{format_slot(valid)}{LAYER_SUFFIX}"
    )


def forecast_payload(
    *,
    piaf: PiafRun | None,
    state: ProductState | None,
    latest: datetime | None,
    now: datetime,
    style: str,
) -> dict[str, Any]:
    """JSON-ready "forecast" object of GET /api/meteofrance_radar/frames.

    Args:
        piaf: The committed PIAF run, None when there is none.
        state: The PIAF product state, None before the first forecast tick.
        latest: Latest stored radar slot, None on an empty archive.
        now: Current aware time.
        style: Current layer style id; a run rendered with another style is ignored.

    Returns:
        {status, source, run, now, frames}, frames being the steps after "now",
        ascending, each with its lead in minutes from "now" and its layer URL.
    """
    marker = now_marker(latest, now)
    usable = piaf if piaf is not None and piaf.style == style else None
    frames: list[dict[str, Any]] = []
    if usable is not None:
        steps = sorted((s for s in usable.steps if s.valid > marker), key=lambda s: s.valid)
        frames = [
            {
                "time": format_iso(step.valid),
                "lead_min": int((step.valid - marker).total_seconds()) // SECONDS_PER_MINUTE,
                "url": forecast_layer_url(style, usable.run, step.valid),
            }
            for step in steps
        ]
    status = ProductStatus.PENDING if state is None else state.status
    return {
        "status": status.value,
        "source": ForecastProduct.PIAF.value,
        "run": None if usable is None else format_iso(usable.run),
        "now": format_iso(marker),
        "frames": frames,
    }
