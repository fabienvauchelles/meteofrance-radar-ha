"""Focused tests of the history tiers and named periods (pure logic, no public-surface path)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.meteofrance_radar.domain.periods import (
    Period,
    PeriodName,
    parse_period_name,
    resolve_period,
)
from custom_components.meteofrance_radar.domain.slots import SLOT
from custom_components.meteofrance_radar.domain.tiers import (
    Tier,
    bucket_of,
    count_missing,
    expected_buckets,
    gaps_before,
    needs_downgrade,
    plan_thinning,
    tier_of,
)
from custom_components.meteofrance_radar.errors import PeriodError

NOW = datetime(2026, 9, 30, 10, 32, tzinfo=UTC)


def _at(day: int, hour: int, minute: int, month: int = 9) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


def _slots(start: datetime, end: datetime) -> list[datetime]:
    result: list[datetime] = []
    t = start
    while t < end:
        result.append(t)
        t += SLOT
    return result


def test_tier_boundaries_at_exactly_3_hours_and_30_days() -> None:
    assert tier_of(NOW - timedelta(hours=3) + timedelta(seconds=1), NOW) is Tier.FIVE_MIN
    assert tier_of(NOW - timedelta(hours=3), NOW) is Tier.HOURLY
    assert tier_of(NOW - timedelta(days=30) + timedelta(seconds=1), NOW) is Tier.HOURLY
    assert tier_of(NOW - timedelta(days=30), NOW) is Tier.THREE_HOURLY
    assert not needs_downgrade(NOW - timedelta(days=30) + timedelta(seconds=1), NOW)
    assert needs_downgrade(NOW - timedelta(days=30), NOW)
    assert [tier.value for tier in Tier] == ["5min", "1h", "3h"]
    with pytest.raises(ValueError, match="naive"):
        tier_of(datetime(2026, 9, 30, 10, 0), NOW)


def test_buckets_nest_from_slot_to_hour_to_three_hours() -> None:
    recent = _at(30, 9, 45)
    hourly = _at(29, 17, 35)
    old = _at(20, 17, 35, month=8)

    assert bucket_of(recent, NOW) == recent
    assert bucket_of(hourly, NOW) == _at(29, 17, 0)
    assert bucket_of(old, NOW) == _at(20, 15, 0, month=8)
    # The hour bucket of a slot lies inside the 3-hour bucket the slot will join later.
    later = NOW + timedelta(days=31)
    assert bucket_of(bucket_of(hourly, NOW), later) == bucket_of(hourly, later)


def test_thinning_keeps_the_earliest_slot_of_each_bucket() -> None:
    day = _slots(_at(29, 12, 0), _at(29, 14, 0))
    missing_noon = [slot for slot in day if slot != _at(29, 12, 0)]

    assert plan_thinning(day, NOW) == [s for s in day if s not in (_at(29, 12, 0), _at(29, 13, 0))]
    kept = sorted(set(missing_noon) - set(plan_thinning(missing_noon, NOW)))
    assert kept == [_at(29, 12, 5), _at(29, 13, 0)]
    recent = _slots(_at(30, 8, 0), _at(30, 10, 30))
    assert [s for s in plan_thinning(recent, NOW) if s >= NOW - timedelta(hours=3)] == []


def test_thinning_is_idempotent_and_stable_as_frames_age() -> None:
    history = _slots(_at(25, 0, 0, month=8), _at(26, 0, 0, month=8))
    history += _slots(_at(28, 0, 0), _at(30, 10, 30))
    kept = sorted(set(history) - set(plan_thinning(history, NOW)))

    assert plan_thinning(kept, NOW) == []
    three_hourly = [s for s in kept if tier_of(s, NOW) is Tier.THREE_HOURLY]
    assert three_hourly == [_at(25, h, 0, month=8) for h in range(0, 24, 3)]
    later = NOW + timedelta(days=40)
    aged = sorted(set(kept) - set(plan_thinning(kept, later)))
    assert all(s.minute == 0 and s.hour % 3 == 0 for s in aged)
    assert plan_thinning(aged, later) == []


def test_expected_buckets_span_every_tier_boundary() -> None:
    start = NOW - timedelta(days=30, hours=4)
    buckets = expected_buckets(start, _at(30, 10, 35), NOW)

    five_min = [b for b in buckets if b > NOW - timedelta(hours=3)]
    # 3-hourly block 09:00 also takes 10:35-10:55: their hour starts in the 3-hourly tier.
    assert buckets[:3] == [_at(31, 9, 0, month=8), _at(31, 11, 0, month=8), _at(31, 12, 0, month=8)]
    assert five_min == _slots(_at(30, 7, 35), _at(30, 10, 35))
    assert buckets == sorted(set(buckets))
    assert all(b >= start for b in buckets)
    # 07:30 is an hourly slot whose bucket (07:00) starts before the period.
    assert expected_buckets(_at(30, 7, 28), _at(30, 7, 40), NOW) == [_at(30, 7, 35)]
    assert expected_buckets(_at(30, 7, 32), _at(30, 7, 32), NOW) == []


def test_count_missing_uses_buckets_not_slots() -> None:
    start, end = _at(30, 5, 0), _at(30, 10, 35)
    present = [_at(30, 5, 5), _at(30, 7, 0), *_slots(_at(30, 7, 35), end)]

    assert count_missing(present, start, end, NOW) == 1
    assert count_missing([], start, end, NOW) == 3 + 36


def test_gaps_before_reports_jumps_over_empty_buckets_only() -> None:
    slots = [
        _at(29, 12, 0),
        _at(29, 13, 5),
        _at(29, 15, 0),
        _at(30, 6, 0),
        _at(30, 7, 0),
        _at(30, 7, 35),
        _at(30, 7, 40),
        _at(30, 8, 5),
    ]

    assert gaps_before(slots, NOW) == [0, 0, 115, 900, 0, 0, 0, 25]
    assert gaps_before([], NOW) == []


@pytest.mark.parametrize(
    ("name", "start"),
    [
        (PeriodName.THREE_HOURS, _at(30, 7, 35)),
        (PeriodName.DAY, _at(29, 10, 35)),
        (PeriodName.WEEK, _at(23, 10, 35)),
        (PeriodName.MONTH, _at(31, 10, 35, month=8)),
        (PeriodName.ALL, _at(1, 0, 0, month=6)),
    ],
)
def test_resolve_period_anchors_on_latest(name: PeriodName, start: datetime) -> None:
    oldest = _at(1, 0, 0, month=6)
    latest = _at(30, 10, 30)

    assert resolve_period(name, oldest, latest) == Period(name, start, _at(30, 10, 35))


def test_resolve_period_clips_to_oldest_and_handles_an_empty_archive() -> None:
    oldest = _at(30, 9, 0)
    latest = _at(30, 10, 30)

    assert resolve_period(PeriodName.DAY, oldest, latest) == Period(
        PeriodName.DAY, oldest, _at(30, 10, 35)
    )
    assert resolve_period(PeriodName.ALL, None, None) is None
    assert resolve_period(PeriodName.THREE_HOURS, None, None) is None


def test_parse_period_name_defaults_to_3h_and_refuses_unknown_names() -> None:
    assert parse_period_name(None) is PeriodName.THREE_HOURS
    assert parse_period_name("7d") is PeriodName.WEEK
    for bad in ("", "3H", "1y", "24"):
        with pytest.raises(PeriodError, match="unknown period"):
            parse_period_name(bad)


def test_thirty_day_boundary_inside_an_hour_reports_no_gap() -> None:
    # Boundary at 08-31 10:32: hour 10 straddles it. Steady archive after hourly thinning.
    kept = [_at(31, 9, 0, month=8), *(_at(31, h, 0, month=8) for h in range(11, 16))]
    aged = [_at(31, 9, 0, month=8), _at(31, 10, 0, month=8), *kept[1:]]

    assert bucket_of(_at(31, 10, 40, month=8), NOW) == _at(31, 9, 0, month=8)
    assert plan_thinning(aged, NOW) == [_at(31, 10, 0, month=8)]
    assert gaps_before(kept, NOW) == [0] * len(kept)
    assert count_missing(kept, kept[0], kept[-1] + SLOT, NOW) == 0
