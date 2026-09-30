"""One forecast tick: PIAF maps, then the AROME-PI and AROME pin series.

Each product fails on its own: a refused or broken API only changes that product's
status. When the key has expired or the radar API refused it, the tick makes no request
at all and the states stay as they were.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol

from ..domain.forecast import ForecastProduct, ForecastState, ProductState, initial_state
from .arome_job import AromePinJob
from .aromepi_job import AromePiPinJob
from .piaf_job import PiafMapsJob

_LOGGER = logging.getLogger(__name__)


class ForecastJob(Protocol):
    """One product's job: `run` never raises for API, decode or storage errors."""

    async def run(self, now: datetime) -> ProductState:
        """Do what is due at `now` and return the product state."""
        ...


class ForecastService:
    """Runs the three forecast jobs in order and keeps their states.

    Args:
        piaf: PIAF nowcast maps.
        aromepi: AROME-PI pin series.
        arome: AROME pin series.
    """

    def __init__(self, *, piaf: PiafMapsJob, aromepi: AromePiPinJob, arome: AromePinJob) -> None:
        self._jobs: dict[ForecastProduct, ForecastJob] = {
            ForecastProduct.PIAF: piaf,
            ForecastProduct.AROMEPI: aromepi,
            ForecastProduct.AROME: arome,
        }
        self._state = initial_state()

    @property
    def state(self) -> ForecastState:
        """States after the last tick (all PENDING before the first one)."""
        return self._state

    async def run_tick(self, now: datetime, *, api_allowed: bool) -> ForecastState:
        """Run every job that is due. With `api_allowed` False, nothing is requested."""
        if not api_allowed:
            _LOGGER.debug("Forecast tick skipped: the API key is expired or refused")
            return self._state
        products = dict(self._state.products)
        for product, job in self._jobs.items():
            products[product] = await job.run(now)
        self._state = ForecastState(products=products)
        return self._state
