"""Request pacing with a fake clock: minimum spacing and the rolling one-minute cap."""

from __future__ import annotations

import asyncio

import pytest

from custom_components.meteofrance_radar.api.pacer import RequestPacer


class FakeClock:
    """Monotonic clock that only moves when the pacer sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _pacer(clock: FakeClock, *, max_per_minute: int, spacing: float) -> RequestPacer:
    return RequestPacer(
        max_per_minute=max_per_minute,
        min_spacing_s=spacing,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )


async def test_requests_are_spaced() -> None:
    clock = FakeClock()
    pacer = _pacer(clock, max_per_minute=90, spacing=0.7)

    starts = []
    for _ in range(3):
        await pacer.wait()
        starts.append(clock.now)

    assert starts == pytest.approx([1000.0, 1000.7, 1001.4])
    assert pacer.requests_last_minute() == 3


async def test_no_wait_when_the_spacing_has_already_passed() -> None:
    clock = FakeClock()
    pacer = _pacer(clock, max_per_minute=90, spacing=0.7)

    await pacer.wait()
    clock.now += 5
    await pacer.wait()

    assert clock.sleeps == []


async def test_rolling_minute_cap_holds_the_next_request() -> None:
    clock = FakeClock()
    pacer = _pacer(clock, max_per_minute=90, spacing=0.0)

    for _ in range(90):
        await pacer.wait()
    assert clock.sleeps == []
    await pacer.wait()

    assert clock.now == pytest.approx(1060.0)
    assert pacer.requests_last_minute() == 1
    clock.now += 61
    assert pacer.requests_last_minute() == 0


async def test_any_minute_stays_under_the_cap() -> None:
    clock = FakeClock()
    pacer = _pacer(clock, max_per_minute=90, spacing=0.3)

    starts = []
    for _ in range(250):
        await pacer.wait()
        starts.append(clock.now)

    for i, start in enumerate(starts):
        assert sum(1 for t in starts[i:] if t < start + 60) <= 90


async def test_concurrent_waiters_are_serialised() -> None:
    clock = FakeClock()
    pacer = _pacer(clock, max_per_minute=90, spacing=1.0)

    await asyncio.gather(*(pacer.wait() for _ in range(4)))

    assert clock.now == pytest.approx(1003.0)


def test_limits_are_validated() -> None:
    clock = FakeClock()
    with pytest.raises(ValueError, match="max_per_minute"):
        _pacer(clock, max_per_minute=0, spacing=0.7)
    with pytest.raises(ValueError, match="min_spacing_s"):
        _pacer(clock, max_per_minute=10, spacing=-1)
