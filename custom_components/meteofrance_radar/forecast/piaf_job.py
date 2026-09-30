"""PIAF nowcast maps: one run every 15 minutes, 20 steps rendered to layer PNGs.

PIAF publishes a run every 5 minutes, about 9 minutes after its run time. The job takes
the runs on the quarter hour, found with a cheap DescribeCoverage on the expected run id
from run + 8 minutes. Each of the 20 steps is one full-bbox GRIB2 (3.5 MB) that lives in
memory only until its layer is rendered and staged. The run is committed once every step
is staged, so a card never sees half a run. A failed run resumes from the staged steps;
after three failures it is committed if the first hour is complete, else dropped.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from functools import partial
from typing import Final

import numpy as np

from ..collector import BlockingRunner
from ..decode.grib import read_grib2
from ..decode.latlon import LatLonTableCache, latlon_cell
from ..domain.forecast import (
    MM_H_FACTOR,
    PIAF_BBOX,
    PIAF_GIVE_UP,
    PIAF_LATENCY,
    PIAF_LEADS_MIN,
    PIAF_RUN_STEP,
    CoverageTimes,
    ForecastProduct,
    PiafRun,
    PiafStep,
    ProductState,
    coverage_id,
    floor_run,
)
from ..domain.grid import TargetGrid
from ..domain.ports import CoverageSource, ForecastStore
from ..domain.slots import format_slot
from ..errors import ApiAuthError, ApiError, InvalidProductError
from ..render.forecast import render_field_layer
from .backoff import ProductTracker
from .pin_fetch import HomeProvider

_LOGGER = logging.getLogger(__name__)

PRODUCT: Final = ForecastProduct.PIAF
MAX_RUN_ATTEMPTS: Final = 3
FIRST_HOUR_LEAD_MIN: Final = 60
FIRST_HOUR_STEPS: Final = sum(1 for lead in PIAF_LEADS_MIN if lead <= FIRST_HOUR_LEAD_MIN)


class PiafMapsJob:
    """Fetches, renders and commits the latest quarter-hour PIAF run.

    Args:
        source: PIAF WCS client.
        store: Forecast store (blocking, called through `run_blocking`).
        tables: Lat/lon to target grid tables, shared with nothing else.
        grid: Target grid of every layer (the radar one).
        style: Current layer style id.
        home: Returns the home (lon, lat), or None when unset.
        run_blocking: Runs a blocking callable in the executor.
        render_lock: The radar layer render lock: one render at a time per process.
    """

    def __init__(
        self,
        source: CoverageSource,
        store: ForecastStore,
        tables: LatLonTableCache,
        grid: TargetGrid,
        style: str,
        home: HomeProvider,
        run_blocking: BlockingRunner,
        render_lock: threading.Lock,
    ) -> None:
        self._source = source
        self._store = store
        self._tables = tables
        self._grid = grid
        self._style = style
        self._home = home
        self._run_blocking = run_blocking
        self._render_lock = render_lock
        self._tracker = ProductTracker(PRODUCT)
        self._expected: datetime | None = None
        self._cold = True
        self._staging: datetime | None = None
        self._staging_pin: tuple[float, float] | None = None
        self._pins: dict[datetime, float | None] = {}
        self._attempts = 0

    @property
    def state(self) -> ProductState:
        """Status after the last run."""
        return self._tracker.state

    async def run(self, now: datetime) -> ProductState:
        """Look for the expected run and fetch it when published. Never raises for API errors."""
        if not self._tracker.due(now):
            return self.state
        try:
            await self._tick(now)
        except ApiAuthError as exc:
            self._tracker.forbidden(now, exc)
        except (ApiError, InvalidProductError, OSError) as exc:
            self._tracker.error(now, exc)
            await self._after_failure(now)
        return self.state

    async def _tick(self, now: datetime) -> None:
        expected = await self._expected_run(now)
        if now < expected + PIAF_LATENCY:
            self._tracker.waiting(expected + PIAF_LATENCY)
            return
        times = await self._source.describe(coverage_id(PRODUCT, expected))
        if times is None and self._cold:
            self._cold = False
            earlier = expected - PIAF_RUN_STEP
            times = await self._source.describe(coverage_id(PRODUCT, earlier))
            if times is not None:
                expected = self._expected = earlier
        if times is None and self._staging == expected:
            # A half-fetched run that vanished counts as a failed attempt, so it is dropped.
            raise ApiError(f"PIAF run {format_slot(expected)} is no longer published")
        if times is None:
            self._tracker.waiting(None)
            return
        self._cold = False
        await self._fetch_run(now, expected, times)

    async def _expected_run(self, now: datetime) -> datetime:
        if self._expected is None:
            current = await self._run_blocking(self._store.current_piaf)
            if current is not None:
                self._cold = False
                self._tracker.run = current.run
                self._expected = current.run + PIAF_RUN_STEP
            else:
                self._expected = floor_run(now - PIAF_LATENCY, PIAF_RUN_STEP)
        if self._staging != self._expected and now > self._expected + PIAF_GIVE_UP:
            # Too late for this run (missed, or HA was down): skip to the latest one.
            self._expected = floor_run(now - PIAF_LATENCY, PIAF_RUN_STEP)
        return self._expected

    async def _fetch_run(self, now: datetime, run: datetime, times: CoverageTimes) -> None:
        published = set(times.valid_times)
        steps = [
            (lead, valid) for lead in PIAF_LEADS_MIN if (valid := run + _minutes(lead)) in published
        ]
        if not steps:
            raise ApiError(f"PIAF run {format_slot(run)} offers none of the expected steps")
        if self._staging != run:
            await self._run_blocking(partial(self._store.begin_run, run))
            self._staging = run
            self._staging_pin = self._piaf_pin()
            self._pins = {}
            self._attempts = 0
        staged = set(await self._run_blocking(partial(self._store.staged, run)))
        cov = coverage_id(PRODUCT, run)
        for _lead, valid in steps:
            if valid in staged and valid in self._pins:
                continue
            data = await self._source.get_grib(cov, valid, PIAF_BBOX)
            self._pins[valid] = await self._run_blocking(
                partial(self._render_step, run, valid, data, self._staging_pin)
            )
            del data
        await self._commit(now, run, steps)

    async def _commit(
        self, now: datetime, run: datetime, steps: list[tuple[int, datetime]]
    ) -> None:
        piaf = PiafRun(
            run=run,
            style=self._style,
            steps=tuple(PiafStep(valid, lead, self._pins.get(valid)) for lead, valid in steps),
            pin=self._staging_pin,
        )
        await self._run_blocking(partial(self._store.commit_run, piaf))
        _LOGGER.debug("Committed PIAF run %s with %d steps", format_slot(run), len(steps))
        self._staging = None
        self._pins = {}
        self._attempts = 0
        self._expected = run + PIAF_RUN_STEP
        self._tracker.ok(now, run, self._expected + PIAF_LATENCY)

    async def _after_failure(self, now: datetime) -> None:
        """After three failed attempts on one run, keep its first hour or drop it."""
        run = self._staging
        if run is None:
            return
        self._attempts += 1
        if self._attempts < MAX_RUN_ATTEMPTS:
            return
        try:
            staged = set(await self._run_blocking(partial(self._store.staged, run)))
            done = [
                (lead, run + _minutes(lead))
                for lead in PIAF_LEADS_MIN
                if run + _minutes(lead) in staged and run + _minutes(lead) in self._pins
            ]
            if sum(1 for lead, _ in done if lead <= FIRST_HOUR_LEAD_MIN) >= FIRST_HOUR_STEPS:
                await self._commit(now, run, done)
                return
        except OSError as exc:
            _LOGGER.debug("Could not commit the partial PIAF run: %s", exc)
        _LOGGER.debug("Dropped PIAF run %s after %d attempts", format_slot(run), self._attempts)
        self._staging = None
        self._pins = {}
        self._attempts = 0
        self._expected = max(floor_run(now - PIAF_LATENCY, PIAF_RUN_STEP), run + PIAF_RUN_STEP)

    def _piaf_pin(self) -> tuple[float, float] | None:
        point = self._home()
        if point is None or not PIAF_BBOX.contains(*point):
            return None
        return point

    def _render_step(
        self, run: datetime, valid: datetime, data: bytes, pin: tuple[float, float] | None
    ) -> float | None:
        """Decode, scale to mm/h, read the pin, render and stage one step (blocking)."""
        field = read_grib2(data)
        mm_h = field.values * np.float32(MM_H_FACTOR[PRODUCT])
        pin_value: float | None = None
        if pin is not None and (cell := latlon_cell(field.grid, *pin)) is not None:
            value = float(mm_h[cell])
            pin_value = max(value, 0.0) if np.isfinite(value) else None
        with self._render_lock:
            table = self._tables.get(field.grid, self._grid)
            png = render_field_layer(mm_h, table)
        self._store.stage_layer(run, valid, png)
        return pin_value


def _minutes(lead: int) -> timedelta:
    return timedelta(minutes=lead)
