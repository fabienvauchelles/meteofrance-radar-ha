"""AROME-PI rain rate at the home: 24 quarter-hour values per hourly run.

Runs are published 20 to 53 minutes after the hour. From run + 20 minutes the expected
run id is checked every 2 minutes; after 90 minutes it is given up and the next hour is
expected (a missed run is never back-filled). A published run costs 24 tiny-bbox
requests. When the home moves, the saved run is fetched again once at the new place.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import Final

from ..collector import BlockingRunner
from ..domain.forecast import (
    AROMEPI_GIVE_UP,
    AROMEPI_LATENCY,
    AROMEPI_RECHECK,
    AROMEPI_RUN_STEP,
    CoverageTimes,
    ForecastProduct,
    PinSeries,
    ProductState,
    coverage_id,
    floor_run,
    same_pin,
)
from ..domain.ports import CoverageSource, ForecastStore
from ..errors import ApiAuthError, ApiError, InvalidProductError
from .backoff import ProductTracker
from .pin_fetch import HomeProvider, fetch_pin_values, home_in_domain

PRODUCT: Final = ForecastProduct.AROMEPI
_EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)


class AromePiPinJob:
    """Keeps the AROME-PI pin series of the latest hourly run.

    Args:
        source: AROME-PI WCS client.
        store: Forecast store (blocking, called through `run_blocking`).
        home: Returns the home (lon, lat), or None when unset.
        run_blocking: Runs a blocking callable in the executor.
    """

    def __init__(
        self,
        source: CoverageSource,
        store: ForecastStore,
        home: HomeProvider,
        run_blocking: BlockingRunner,
    ) -> None:
        self._source = source
        self._store = store
        self._home = home
        self._run_blocking = run_blocking
        self._tracker = ProductTracker(PRODUCT)
        self._expected: datetime | None = None
        self._cold = True
        self._last_check: datetime | None = None
        self._moved_run: datetime | None = None

    @property
    def state(self) -> ProductState:
        """Status after the last run."""
        return self._tracker.state

    async def run(self, now: datetime) -> ProductState:
        """Fetch the expected run once published. Never raises for API errors."""
        home = home_in_domain(self._home)
        if home is None:
            self._tracker.outside()
            return self.state
        if not self._tracker.due(now):
            return self.state
        try:
            await self._tick(now, home)
        except ApiAuthError as exc:
            self._tracker.forbidden(now, exc)
        except (ApiError, InvalidProductError, OSError) as exc:
            self._tracker.error(now, exc)
        return self.state

    async def _tick(self, now: datetime, home: tuple[float, float]) -> None:
        saved = await self._run_blocking(partial(self._store.pin_series, PRODUCT))
        if saved is not None:
            self._tracker.run = saved.run
            if not same_pin((saved.lon, saved.lat), home) and self._moved_run != saved.run:
                self._moved_run = saved.run
                times = await self._source.describe(coverage_id(PRODUCT, saved.run))
                if times is not None:
                    await self._fetch(now, saved.run, times, home)
                    return
        expected = self._expected_run(now, saved)
        check_at = max(expected + AROMEPI_LATENCY, self._next_recheck())
        if now < check_at:
            self._tracker.waiting(check_at)
            return
        self._last_check = now
        times = await self._source.describe(coverage_id(PRODUCT, expected))
        if times is None and self._cold:
            self._cold = False
            earlier = expected - AROMEPI_RUN_STEP
            times = await self._source.describe(coverage_id(PRODUCT, earlier))
            if times is not None:
                expected = earlier
        self._cold = False
        if times is None:
            self._tracker.waiting(now + AROMEPI_RECHECK)
            return
        await self._fetch(now, expected, times, home)

    def _expected_run(self, now: datetime, saved: PinSeries | None) -> datetime:
        if self._expected is None or (saved is not None and saved.run >= self._expected):
            if saved is not None:
                self._cold = False
                self._expected = saved.run + AROMEPI_RUN_STEP
            else:
                self._expected = floor_run(now - AROMEPI_LATENCY, AROMEPI_RUN_STEP)
        if now > self._expected + AROMEPI_GIVE_UP:
            # Too late for this run (missed, or HA was down): skip to the latest one.
            self._expected = floor_run(now - AROMEPI_LATENCY, AROMEPI_RUN_STEP)
        return self._expected

    def _next_recheck(self) -> datetime:
        if self._last_check is None:
            return _EPOCH
        return self._last_check + AROMEPI_RECHECK

    async def _fetch(
        self, now: datetime, run: datetime, times: CoverageTimes, home: tuple[float, float]
    ) -> None:
        values = await fetch_pin_values(
            self._source, PRODUCT, run, times.valid_times, home, self._run_blocking
        )
        series = PinSeries(product=PRODUCT, run=run, lon=home[0], lat=home[1], values=tuple(values))
        await self._run_blocking(partial(self._store.save_pin_series, series))
        self._moved_run = None
        self._expected = run + AROMEPI_RUN_STEP
        self._tracker.ok(now, run, self._expected + AROMEPI_LATENCY)
