"""Rain bar window, segment classes and stitching, plus forecast ids and run flooring.

Pure domain logic: focused tests.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from custom_components.meteofrance_radar.domain.forecast import (
    AROME_RUN_STEP,
    PIAF_LEADS_MIN,
    PIAF_RUN_STEP,
    ForecastProduct,
    PinValue,
    ProductStatus,
    coverage_id,
    floor_run,
    initial_state,
    parse_run_id,
    pin_bbox,
    run_id,
    same_pin,
)
from custom_components.meteofrance_radar.domain.pin_series import (
    BarWindow,
    Segment,
    SegmentSource,
    bar_window,
    class_of,
    piaf_segment_length,
    segments_ending_at,
    stitch,
)

MIN5 = timedelta(minutes=5)
MIN15 = timedelta(minutes=15)
HOUR = timedelta(hours=1)


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


@pytest.mark.parametrize(
    ("now", "end"),
    [
        # Summer time (UTC+2), 17:07 Paris: midnight Paris is 22:00 UTC, beyond +6 h.
        (_utc(2026, 9, 30, 15, 7), _utc(2026, 9, 30, 22, 0)),
        # Summer time, 19:00 Paris (after 18:00): +6 h wins.
        (_utc(2026, 9, 30, 17, 0), _utc(2026, 9, 30, 23, 0)),
        # Summer time, exactly 18:00 Paris: both rules agree.
        (_utc(2026, 9, 30, 16, 0), _utc(2026, 9, 30, 22, 0)),
        # Winter time (UTC+1), 10:00 Paris: midnight is 23:00 UTC.
        (_utc(2026, 1, 15, 9, 0), _utc(2026, 1, 15, 23, 0)),
        # Winter time, 23:30 Paris: +6 h, not the midnight 30 minutes away.
        (_utc(2026, 1, 15, 22, 30), _utc(2026, 1, 16, 4, 30)),
        # Exactly midnight Paris: the next midnight is a day later.
        (_utc(2026, 1, 15, 23, 0), _utc(2026, 1, 16, 23, 0)),
        # Clocks go back on 2026-10-25: 02:00 Paris (UTC+2) to midnight (UTC+1) is 23 h.
        (_utc(2026, 10, 25, 0, 0), _utc(2026, 10, 25, 23, 0)),
        # Clocks go forward on 2026-03-29: midnight after is at 22:00 UTC.
        (_utc(2026, 3, 29, 9, 0), _utc(2026, 3, 29, 22, 0)),
    ],
)
def test_bar_window(now: datetime, end: datetime) -> None:
    window = bar_window(now)

    assert window.start == now - timedelta(hours=3)
    assert window.end == end


def test_bar_window_refuses_naive_times() -> None:
    with pytest.raises(ValueError, match="timezone"):
        bar_window(datetime(2026, 9, 30, 15, 0))


def test_class_of_follows_the_palette() -> None:
    assert class_of(0.0) == 0
    assert class_of(0.05) == 0
    assert class_of(0.1) == 1
    assert class_of(1.2) == 3
    assert class_of(129.0) == 10
    assert class_of(None) == 11
    assert class_of(math.nan) == 11


def test_piaf_lengths_and_leads() -> None:
    assert len(PIAF_LEADS_MIN) == 20
    assert PIAF_LEADS_MIN[:3] == (5, 10, 15)
    assert PIAF_LEADS_MIN[11:14] == (60, 75, 90)
    assert PIAF_LEADS_MIN[-1] == 180
    assert piaf_segment_length(60) == MIN5
    assert piaf_segment_length(75) == MIN15


def test_segments_end_at_their_valid_time() -> None:
    run = _utc(2026, 9, 30, 15, 0)
    values = [(run + timedelta(minutes=75), 2.0), (run + MIN5, math.nan)]

    segments = segments_ending_at(
        SegmentSource.PIAF,
        values,
        lambda valid: piaf_segment_length(int((valid - run).total_seconds() // 60)),
    )

    assert segments == [
        Segment(SegmentSource.PIAF, run, run + MIN5, None, 11),
        Segment(
            SegmentSource.PIAF, run + timedelta(minutes=60), run + timedelta(minutes=75), 2.0, 4
        ),
    ]


def _series(source: SegmentSource, start: datetime, count: int, step: timedelta) -> list[Segment]:
    return segments_ending_at(source, [(start + step * (i + 1), 0.5) for i in range(count)], step)


NOW = _utc(2026, 9, 30, 15, 0)
WINDOW = BarWindow(start=NOW - timedelta(hours=3), end=NOW + timedelta(hours=7))
RADAR = _series(SegmentSource.RADAR, NOW - timedelta(hours=3, minutes=5), 37, MIN5)
PIAF = _series(SegmentSource.PIAF, NOW - timedelta(minutes=10), 36, MIN5)
AROMEPI = _series(SegmentSource.AROMEPI, NOW - HOUR, 28, MIN15)
AROME = _series(SegmentSource.AROME, NOW - timedelta(hours=3), 12, HOUR)


def _check_ordered(segments: list[Segment]) -> None:
    for before, after in pairwise(segments):
        assert before.end <= after.start
    for segment in segments:
        assert WINDOW.start <= segment.start < segment.end <= WINDOW.end


def _span(segments: list[Segment], source: SegmentSource) -> tuple[datetime, datetime]:
    own = [s for s in segments if s.source is source]
    return own[0].start, own[-1].end


def test_stitch_all_sources_in_order() -> None:
    segments = stitch(RADAR, [PIAF, AROMEPI, AROME], WINDOW)

    _check_ordered(segments)
    assert _span(segments, SegmentSource.RADAR) == (WINDOW.start, NOW)
    assert _span(segments, SegmentSource.PIAF) == (NOW, NOW + timedelta(hours=2, minutes=50))
    assert _span(segments, SegmentSource.AROMEPI) == (
        NOW + timedelta(hours=2, minutes=50),
        NOW + timedelta(hours=6),
    )
    assert _span(segments, SegmentSource.AROME) == (NOW + timedelta(hours=6), WINDOW.end)
    assert segments[0].start == WINDOW.start


def test_stitch_without_piaf_starts_aromepi_at_the_radar_end() -> None:
    segments = stitch(RADAR, [[], AROMEPI, AROME], WINDOW)

    _check_ordered(segments)
    assert _span(segments, SegmentSource.AROMEPI)[0] == NOW
    clipped = next(s for s in segments if s.source is SegmentSource.AROMEPI)
    assert clipped.end - clipped.start == MIN15


def test_stitch_without_radar_starts_at_the_window() -> None:
    segments = stitch([], [PIAF, AROMEPI, AROME], WINDOW)

    _check_ordered(segments)
    # PIAF comes first, so AROME never fills the past before it.
    assert segments[0].source is SegmentSource.PIAF
    assert segments[0].start == NOW - timedelta(minutes=10)
    assert _span(segments, SegmentSource.AROME) == (NOW + timedelta(hours=6), WINDOW.end)


def test_stitch_keeps_radar_gaps_and_clips_overlaps() -> None:
    radar = [s for i, s in enumerate(RADAR) if i not in (10, 11)]
    piaf = [Segment(SegmentSource.PIAF, NOW - MIN5 * 3, NOW + MIN5, 1.0, 3)]

    segments = stitch(radar, [piaf], WINDOW)

    _check_ordered(segments)
    assert len([s for s in segments if s.source is SegmentSource.RADAR]) == 34
    assert segments[-1] == Segment(SegmentSource.PIAF, NOW, NOW + MIN5, 1.0, 3)


def test_forecast_ids_and_run_flooring() -> None:
    run = _utc(2026, 9, 30, 14, 50)

    assert run_id(run) == "2026-09-30T14.50.00Z"
    assert parse_run_id(run_id(run)) == run
    assert coverage_id(ForecastProduct.PIAF, run).endswith("___2026-09-30T14.50.00Z_PT5M")
    assert coverage_id(ForecastProduct.AROMEPI, run) == (
        "TOTAL_PRECIPITATION_RATE__GROUND_OR_WATER_SURFACE___2026-09-30T14.50.00Z"
    )
    assert coverage_id(ForecastProduct.AROME, run).startswith("TOTAL_PRECIPITATION__")
    assert floor_run(_utc(2026, 9, 30, 14, 59, 59), PIAF_RUN_STEP) == _utc(2026, 9, 30, 14, 45)
    assert floor_run(_utc(2026, 9, 30, 14, 0), AROME_RUN_STEP) == _utc(2026, 9, 30, 12, 0)
    assert pin_bbox(2.46, 48.80).subsets() == ("long(2.445,2.475)", "lat(48.785,48.815)")


def test_states_pins_and_values() -> None:
    state = initial_state()

    assert set(state.products) == set(ForecastProduct)
    assert state.of(ForecastProduct.AROME).status is ProductStatus.PENDING
    assert same_pin((2.46, 48.8), (2.4600001, 48.8))
    assert not same_pin((2.46, 48.8), (2.47, 48.8))
    assert same_pin(None, None)
    assert not same_pin(None, (2.46, 48.8))
    with pytest.raises(ValueError, match="pin rate"):
        PinValue(NOW, -1.0)
