"""5-minute UTC slot arithmetic: parse, format, round."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Final

SLOT: Final = timedelta(minutes=5)
SLOT_FORMAT: Final = "%Y%m%dT%H%MZ"
ISO_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
_SLOT_TEXT = re.compile(r"^\d{8}T\d{4}Z$")
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def require_aware(t: datetime) -> None:
    """Refuse a naive datetime.

    Raises:
        ValueError: t is naive.
    """
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError(f"naive datetime not allowed: {t.isoformat()}")


def is_slot(t: datetime) -> bool:
    """Return True when t is an aware time on the 5-minute grid.

    Raises:
        ValueError: t is naive.
    """
    require_aware(t)
    utc = t.astimezone(UTC)
    return utc.minute % 5 == 0 and utc.second == 0 and utc.microsecond == 0


def format_slot(slot: datetime) -> str:
    """Format a slot as "YYYYMMDDTHHMMZ" in UTC.

    Raises:
        ValueError: slot is naive.
    """
    require_aware(slot)
    return slot.astimezone(UTC).strftime(SLOT_FORMAT)


def format_iso(t: datetime) -> str:
    """Format a time as "YYYY-MM-DDTHH:MM:SSZ" in UTC, as the frames API returns it.

    Raises:
        ValueError: t is naive.
    """
    require_aware(t)
    return t.astimezone(UTC).strftime(ISO_FORMAT)


def parse_slot(text: str) -> datetime:
    """Parse "YYYYMMDDTHHMMZ" into an aware UTC slot.

    Raises:
        ValueError: text is malformed or not on the 5-minute grid.
    """
    if not _SLOT_TEXT.match(text):
        raise ValueError(f"not a slot: {text!r}")
    slot = datetime.strptime(text, SLOT_FORMAT).replace(tzinfo=UTC)
    if not is_slot(slot):
        raise ValueError(f"not on the 5-minute grid: {text!r}")
    return slot


def floor_slot(t: datetime) -> datetime:
    """Return the largest slot <= t, in UTC.

    Raises:
        ValueError: t is naive.
    """
    require_aware(t)
    utc = t.astimezone(UTC)
    return utc - (utc - _EPOCH) % SLOT


def ceil_slot(t: datetime) -> datetime:
    """Return the smallest slot >= t, in UTC.

    Raises:
        ValueError: t is naive.
    """
    floor = floor_slot(t)
    return floor if floor == t else floor + SLOT
