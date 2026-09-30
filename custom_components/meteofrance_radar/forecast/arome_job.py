"""AROME hourly rain at the home, up to the end of the rain bar.

AROME runs every 3 hours and publishes its hourly steps progressively. Once an hour the
job asks whether the next run is out and far enough ahead to replace the saved one; if
not, it asks the saved run for newly published steps. Only hourly values the saved
series does not hold yet are fetched, each one a tiny-bbox request.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import partial
from typing import Final

from ..collector import BlockingRunner
from ..domain.forecast import (
    AROME_RECHECK,
    AROME_RUN_STEP,
    CoverageTimes,
    ForecastProduct,
    PinSeries,
    PinValue,
    ProductState,
    coverage_id,
    floor_run,
    same_pin,
)
from ..domain.pin_series import bar_window
from ..domain.ports import CoverageSource, ForecastStore
from ..errors import ApiAuthError, ApiError, InvalidProductError
from .backoff import ProductTracker
from .pin_fetch import HomeProvider, fetch_pin_values, home_in_domain

PRODUCT: Final = ForecastProduct.AROME
COLD_RUNS_BACK: Final = 3
STALE_RUNS: Final = 2
MAX_FETCH: Final = 24
KEEP_PAST: Final = timedelta(hours=1)
ACCUMULATION: Final = timedelta(hours=1)


class AromePinJob:
    """Keeps the AROME pin series of the latest useful run, step by step.

    Args:
        source: AROME WCS client.
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
        self._last_check: datetime | None = None
        self._times: CoverageTimes | None = None

    @property
    def state(self) -> ProductState:
        """Status after the last run."""
        return self._tracker.state

    async def run(self, now: datetime) -> ProductState:
        """Hourly: pick the run and fetch its new steps. Never raises for API errors."""
        home = home_in_domain(self._home)
        if home is None:
            self._tracker.outside()
            return self.state
        if not self._tracker.due(now):
            return self.state
        if self._last_check is not None and now < self._last_check + AROME_RECHECK:
            self._tracker.waiting(self._last_check + AROME_RECHECK)
            return self.state
        try:
            await self._tick(now, home)
            self._last_check = now
        except ApiAuthError as exc:
            self._tracker.forbidden(now, exc)
        except (ApiError, InvalidProductError, OSError) as exc:
            self._tracker.error(now, exc)
        return self.state

    async def _tick(self, now: datetime, home: tuple[float, float]) -> None:
        saved = await self._run_blocking(partial(self._store.pin_series, PRODUCT))
        if saved is not None and not same_pin((saved.lon, saved.lat), home):
            saved = PinSeries(PRODUCT, saved.run, home[0], home[1], ())
        end = bar_window(now).end
        times = await self._pick_run(now, saved, end)
        if times is None:
            self._tracker.waiting(now + AROME_RECHECK)
            return
        self._times = times
        held = saved.values if saved is not None and saved.run == times.run else ()
        known = {value.valid for value in held}
        # A value covers the hour ending at its valid time, so the step whose hour holds
        # the window end is needed too when the end is not on the hour.
        wanted = [t for t in times.valid_times if now < t < end + ACCUMULATION and t not in known]
        fetched = await fetch_pin_values(
            self._source, PRODUCT, times.run, wanted[:MAX_FETCH], home, self._run_blocking
        )
        values = sorted((*held, *fetched), key=lambda value: value.valid)
        series = PinSeries(
            product=PRODUCT,
            run=times.run,
            lon=home[0],
            lat=home[1],
            values=tuple(v for v in values if v.valid >= now - KEEP_PAST),
        )
        if fetched or series != saved:
            await self._run_blocking(partial(self._store.save_pin_series, series))
        self._tracker.ok(now, times.run, now + AROME_RECHECK)

    async def _pick_run(
        self, now: datetime, saved: PinSeries | None, end: datetime
    ) -> CoverageTimes | None:
        if saved is None:
            return await self._cold_run(now)
        if saved.run + STALE_RUNS * AROME_RUN_STEP <= floor_run(now, AROME_RUN_STEP):
            # After a long downtime, jump to the latest run instead of one run per hour.
            latest = await self._cold_run(now)
            if latest is not None:
                return latest
        newer_run = saved.run + AROME_RUN_STEP
        if newer_run <= now:
            newer = await self._source.describe(coverage_id(PRODUCT, newer_run))
            if newer is not None and newer.valid_times:
                reach = min(end, self._saved_last_valid(saved))
                if newer.valid_times[-1] >= reach:
                    return newer
        current = await self._source.describe(coverage_id(PRODUCT, saved.run))
        return current if current is not None else await self._cold_run(now)

    async def _cold_run(self, now: datetime) -> CoverageTimes | None:
        latest = floor_run(now, AROME_RUN_STEP)
        for back in range(COLD_RUNS_BACK):
            times = await self._source.describe(
                coverage_id(PRODUCT, latest - back * AROME_RUN_STEP)
            )
            if times is not None:
                return times
        return None

    def _saved_last_valid(self, saved: PinSeries) -> datetime:
        if self._times is not None and self._times.run == saved.run and self._times.valid_times:
            return self._times.valid_times[-1]
        last: PinValue | None = saved.values[-1] if saved.values else None
        return last.valid if last is not None else saved.run
