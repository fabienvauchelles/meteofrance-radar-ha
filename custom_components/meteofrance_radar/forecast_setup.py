"""Builds the forecast side of a loaded entry: store, WCS clients, jobs and coordinator.

The forecast store is opened in the executor at setup. The first forecast tick runs as
an entry background task once the radar is running, so a slow or refused forecast API
never delays the setup, and no forecast request goes out before the radar has had its
chance to report a refused key.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.pacer import RequestPacer
from .api.wcs import WcsClient
from .collector import BlockingRunner
from .const import (
    AROME_WCS_URL,
    AROMEPI_WCS_URL,
    CONF_API_KEY,
    FORECAST_MAX_PER_MINUTE,
    FORECAST_MIN_SPACING_S,
    PIAF_WCS_URL,
)
from .coordinator import RadarCoordinator
from .decode.latlon import LatLonTableCache
from .domain.forecast import ForecastProduct
from .domain.grid import FRANCE_GRID
from .domain.ports import FrameStore
from .forecast.arome_job import AromePinJob
from .forecast.aromepi_job import AromePiPinJob
from .forecast.piaf_job import PiafMapsJob
from .forecast.service import ForecastService
from .forecast_coordinator import ForecastCoordinator
from .pinseries.radar_history import RadarPinHistory
from .render.service import LayerService
from .runtime import ForecastRuntime, RadarConfigEntry
from .store.forecast_store import FileForecastStore

BACKGROUND_TASK_NAME: Final = "meteofrance_radar forecast"
BASE_URLS: Final[dict[ForecastProduct, str]] = {
    ForecastProduct.PIAF: PIAF_WCS_URL,
    ForecastProduct.AROMEPI: AROMEPI_WCS_URL,
    ForecastProduct.AROME: AROME_WCS_URL,
}


def home_provider(hass: HomeAssistant) -> Callable[[], tuple[float, float] | None]:
    """Returns the home (lon, lat) from the core config, None while it is unset (0, 0)."""

    def home() -> tuple[float, float] | None:
        lon, lat = hass.config.longitude, hass.config.latitude
        if lon == 0 and lat == 0:
            return None
        return float(lon), float(lat)

    return home


def executor_runner(hass: HomeAssistant) -> BlockingRunner:
    """Runs blocking callables in Home Assistant's executor."""

    def run[T](func: Callable[[], T], /) -> Awaitable[T]:
        return hass.async_add_executor_job(func)

    return run


async def async_setup_forecast(
    hass: HomeAssistant,
    entry: RadarConfigEntry,
    root: Path,
    frames: FrameStore,
    layers: LayerService,
    radar: RadarCoordinator,
) -> ForecastRuntime:
    """Open the forecast store and build the jobs; nothing is requested yet.

    Raises:
        OSError: the forecast folder cannot be created or read.
    """
    store = FileForecastStore(root)
    await hass.async_add_executor_job(store.load, layers.style)
    session = async_get_clientsession(hass)
    key = entry.data[CONF_API_KEY]
    clients = {
        product: WcsClient(
            session,
            key,
            product.value,
            BASE_URLS[product],
            RequestPacer(
                max_per_minute=FORECAST_MAX_PER_MINUTE, min_spacing_s=FORECAST_MIN_SPACING_S
            ),
        )
        for product in ForecastProduct
    }
    home = home_provider(hass)
    run_blocking = executor_runner(hass)
    service = ForecastService(
        piaf=PiafMapsJob(
            clients[ForecastProduct.PIAF],
            store,
            LatLonTableCache(),
            FRANCE_GRID,
            layers.style,
            home,
            run_blocking,
            layers.render_lock,
        ),
        aromepi=AromePiPinJob(clients[ForecastProduct.AROMEPI], store, home, run_blocking),
        arome=AromePinJob(clients[ForecastProduct.AROME], store, home, run_blocking),
    )
    return ForecastRuntime(
        store=store,
        coordinator=ForecastCoordinator(hass, entry, service, radar),
        pin_history=RadarPinHistory(frames),
        clients=clients,
    )


@callback
def async_start_forecast(hass: HomeAssistant, entry: RadarConfigEntry) -> None:
    """Keep the forecast poll alive and run its first tick in the background."""
    coordinator = entry.runtime_data.forecast.coordinator

    @callback
    def _keep_polling() -> None:
        """Do nothing: without a listener the coordinator stops scheduling ticks."""

    entry.async_on_unload(coordinator.async_add_listener(_keep_polling))
    entry.async_create_background_task(hass, coordinator.async_refresh(), BACKGROUND_TASK_NAME)
