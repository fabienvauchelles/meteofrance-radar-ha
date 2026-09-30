"""History tiers: which frames to keep as they age, and which buckets a period expects.

A frame younger than 3 h is kept at every 5-minute slot, younger than 30 days once per UTC
hour, older once per UTC 3-hour block. Each bucket keeps its earliest frame. Buckets nest
(a 3-hour block starts on an hour, an hour on a slot), so the earliest frame of a 3-hour
bucket is the earliest of its first non-empty hour: thinning is idempotent, and a missed HH:00
is replaced by HH:05 instead of leaving a hole.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Final

from .slots import SLOT, ceil_slot, floor_slot, require_aware

FIVE_MIN_AGE: Final = timedelta(hours=3)
HOURLY_AGE: Final = timedelta(days=30)
_HOUR: Final = timedelta(hours=1)
_THREE_HOURS: Final = timedelta(hours=3)
_MINUTES: Final = timedelta(minutes=1)


class Tier(StrEnum):
    """Keeping resolution of a frame, by age. Values are the frames API labels."""

    FIVE_MIN = "5min"
    HOURLY = "1h"
    THREE_HOURLY = "3h"


def tier_of(slot: datetime, now: datetime) -> Tier:
    """Tier of a slot: 5-minute below 3 h of age, hourly below 30 days, 3-hourly after.

    Raises:
        ValueError: slot or now is naive.
    """
    require_aware(slot)
    require_aware(now)
    age = now - slot
    if age < FIVE_MIN_AGE:
        return Tier.FIVE_MIN
    if age < HOURLY_AGE:
        return Tier.HOURLY
    return Tier.THREE_HOURLY


def _bucket_span(tier: Tier) -> timedelta:
    return {Tier.FIVE_MIN: SLOT, Tier.HOURLY: _HOUR, Tier.THREE_HOURLY: _THREE_HOURS}[tier]


def _floor_to(utc: datetime, tier: Tier) -> datetime:
    if tier is Tier.FIVE_MIN:
        return utc
    hour = utc.replace(minute=0)
    if tier is Tier.HOURLY:
        return hour
    return hour.replace(hour=hour.hour - hour.hour % 3)


def bucket_of(slot: datetime, now: datetime) -> datetime:
    """Start of the bucket holding a slot: itself, its UTC hour or its UTC 3-hour block.

    The tier of a bucket is the tier of its start. An hourly slot whose hour started in the
    3-hourly tier belongs to that 3-hour block, so the 30-day boundary never splits an hour
    into a bucket whose own frame has already been merged into the older block.

    Raises:
        ValueError: slot or now is naive.
    """
    utc = floor_slot(slot)
    tier = tier_of(utc, now)
    bucket = _floor_to(utc, tier)
    start_tier = tier_of(bucket, now)
    return bucket if start_tier is tier else _floor_to(utc, start_tier)


def needs_downgrade(slot: datetime, now: datetime) -> bool:
    """Return True when a slot is in the 3-hourly tier, where frames are stored as classes."""
    return tier_of(slot, now) is Tier.THREE_HOURLY


def plan_thinning(slots: Iterable[datetime], now: datetime) -> list[datetime]:
    """Slots to delete so that each bucket keeps only its earliest slot, ascending.

    Raises:
        ValueError: a slot or now is naive.
    """
    kept: dict[datetime, datetime] = {}
    drop: list[datetime] = []
    for slot in sorted(slots):
        bucket = bucket_of(slot, now)
        if bucket in kept:
            drop.append(slot)
        else:
            kept[bucket] = slot
    return drop


def _next_tier_change(t: datetime, now: datetime) -> datetime | None:
    """First slot after t whose tier differs from the tier of t, or None."""
    boundaries = (now - HOURLY_AGE, now - FIVE_MIN_AGE)
    for boundary in boundaries:
        first = ceil_slot(boundary)
        first = first if first > boundary else first + SLOT
        if first > t:
            return first
    return None


def expected_buckets(start: datetime, end: datetime, now: datetime) -> list[datetime]:
    """Buckets that start in [start, end), for the slots of that range, ascending.

    A bucket that starts before `start` is left out even when some of its slots fall in the
    range: the period does not expect its frame.

    Raises:
        ValueError: start, end or now is naive.
    """
    require_aware(start)
    require_aware(end)
    result: list[datetime] = []
    t = ceil_slot(start)
    end_utc = end.astimezone(UTC)
    while t < end_utc:
        bucket = bucket_of(t, now)
        if bucket >= start and (not result or result[-1] != bucket):
            result.append(bucket)
        # Next bucket start in the tier of t: past the rest of its own hour or block.
        tier = tier_of(t, now)
        following = _floor_to(floor_slot(t), tier) + _bucket_span(tier)
        change = _next_tier_change(t, now)
        if change is not None and change < following:
            following = change
        t = max(following, t + SLOT)
    return result


def _has_empty_bucket_between(previous: datetime, current: datetime, now: datetime) -> bool:
    # Buckets starting after `previous` and before the bucket of `current` hold no frame.
    return bool(expected_buckets(previous + SLOT, bucket_of(current, now), now))


def gaps_before(slots: Sequence[datetime], now: datetime) -> list[int]:
    """Minutes jumped before each slot when an expected bucket before it is empty, else 0.

    Args:
        slots: Stored slots, ascending.
        now: Current aware time, which sets the tier of each slot.

    Returns:
        One value per slot; the first is always 0.

    Raises:
        ValueError: a slot or now is naive.
    """
    result: list[int] = []
    previous: datetime | None = None
    for slot in slots:
        gap = 0
        if previous is not None and _has_empty_bucket_between(previous, slot, now):
            gap = int((slot - previous) / _MINUTES)
        result.append(gap)
        previous = slot
    return result


def count_missing(slots: Iterable[datetime], start: datetime, end: datetime, now: datetime) -> int:
    """Number of expected buckets of [start, end) holding none of the given slots.

    Raises:
        ValueError: a slot, start, end or now is naive.
    """
    present = {bucket_of(slot, now) for slot in slots}
    return sum(1 for bucket in expected_buckets(start, end, now) if bucket not in present)
