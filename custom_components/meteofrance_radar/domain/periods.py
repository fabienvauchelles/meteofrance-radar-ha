"""Named periods of the frames API, anchored on the latest stored slot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Final

from ..errors import PeriodError
from .slots import SLOT, require_aware


class PeriodName(StrEnum):
    """Period names accepted by the frames API and the card."""

    THREE_HOURS = "3h"
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"
    ALL = "all"


DEFAULT_PERIOD: Final = PeriodName.THREE_HOURS
_SPANS: Final[dict[PeriodName, timedelta]] = {
    PeriodName.THREE_HOURS: timedelta(hours=3),
    PeriodName.DAY: timedelta(hours=24),
    PeriodName.WEEK: timedelta(days=7),
    PeriodName.MONTH: timedelta(days=30),
}


@dataclass(frozen=True)
class Period:
    """Half-open UTC period [start, end) resolved from a name."""

    name: PeriodName
    start: datetime
    end: datetime


def parse_period_name(text: str | None) -> PeriodName:
    """Period name from a query value; None gives the default ("3h").

    Raises:
        PeriodError: the value is not a known period name.
    """
    if text is None:
        return DEFAULT_PERIOD
    try:
        return PeriodName(text)
    except ValueError as exc:
        allowed = ", ".join(name.value for name in PeriodName)
        raise PeriodError(f"unknown period {text!r}, expected one of {allowed}") from exc


def resolve_period(
    name: PeriodName, oldest: datetime | None, latest: datetime | None
) -> Period | None:
    """Period of a name: [latest - span + 5 min, latest + 5 min), clipped to oldest.

    "all" is [oldest, latest + 5 min).

    Args:
        name: Period name.
        oldest: Oldest stored slot, None when the archive is empty.
        latest: Latest stored slot, None when the archive is empty.

    Returns:
        The UTC period, or None on an empty archive.

    Raises:
        ValueError: oldest or latest is naive.
    """
    if oldest is None or latest is None:
        return None
    require_aware(oldest)
    require_aware(latest)
    oldest_utc = oldest.astimezone(UTC)
    end = latest.astimezone(UTC) + SLOT
    if name is PeriodName.ALL:
        return Period(name, oldest_utc, end)
    start = max(end - _SPANS[name], oldest_utc)
    return Period(name, start, end)
