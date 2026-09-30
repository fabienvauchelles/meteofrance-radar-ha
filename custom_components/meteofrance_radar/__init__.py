"""Météo-France Radar: collects the 500 m rain mosaic and serves it to a Lovelace card.

``async_setup`` registers the HTTP views, the static files and the card resource once
per Home Assistant run. ``async_setup_entry`` opens the storage root, loads the frame
index and runs one maintenance pass, all in the executor, then starts polling. A
Météo-France outage at startup never blocks the history already on disk, so the first
pass is a plain refresh rather than a first refresh that could fail the setup.
Unloading or removing the entry never deletes stored frames.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .api.client import DPRadarClient
from .collector import BlockingRunner, Collector, free_bytes
from .const import (
    BYTES_PER_MB,
    CONF_API_KEY,
    CONF_SIZE_CAP_MB,
    DEFAULT_SIZE_CAP_MB,
    DOMAIN,
    ISSUE_KEY_EXPIRING,
    LAYER_CACHE_SHARE,
)
from .coordinator import RadarCoordinator
from .decode.odim import read_product
from .decode.reproject import TableCache
from .domain.grid import FRANCE_GRID
from .domain.palette import style_id
from .errors import StoragePathError
from .frontend import async_register_frontend
from .render.service import LayerService
from .runtime import RadarConfigEntry, RadarRuntime, prepare_storage_root, storage_root_of
from .store.frame_store import FileFrameStore
from .store.layer_cache import FileLayerCache
from .store.maintenance import Maintenance
from .views import async_register_views

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class _HassClock:
    """Clock port on Home Assistant's time source (frozen by tests)."""

    def now(self) -> datetime:
        return dt_util.utcnow()


def _executor_runner(hass: HomeAssistant) -> BlockingRunner:
    def run[T](func: Callable[[], T], /) -> Awaitable[T]:
        return hass.async_add_executor_job(func)

    return run


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the views, the static files and the card resource, once per run."""
    async_register_views(hass)
    await async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RadarConfigEntry) -> bool:
    """Open the storage, then start the collector."""
    root = storage_root_of(hass, entry)
    cap_bytes = int(entry.options.get(CONF_SIZE_CAP_MB, DEFAULT_SIZE_CAP_MB)) * BYTES_PER_MB
    style = style_id(FRANCE_GRID)
    store = FileFrameStore(root)
    layer_cache = FileLayerCache(root)
    maintenance = Maintenance(store, layer_cache, _HassClock(), style, cap_bytes, LAYER_CACHE_SHARE)

    def open_storage() -> None:
        prepare_storage_root(root)
        store.load_index()
        layer_cache.purge_other_styles(style)
        maintenance.run()

    try:
        await hass.async_add_executor_job(open_storage)
    except StoragePathError as exc:
        raise ConfigEntryNotReady(str(exc)) from exc
    except OSError as exc:
        raise ConfigEntryNotReady(f"cannot open storage {root}: {exc}") from exc

    run_blocking = _executor_runner(hass)
    collector = Collector(
        source=DPRadarClient(async_get_clientsession(hass), entry.data[CONF_API_KEY]),
        store=store,
        decode=read_product,
        free_space=lambda: free_bytes(root),
        maintain=maintenance.run,
        run_blocking=run_blocking,
    )
    coordinator = RadarCoordinator(hass, entry, collector)
    integration = await async_get_integration(hass, DOMAIN)
    entry.runtime_data = RadarRuntime(
        store=store,
        layers=LayerService(store, layer_cache, TableCache(), FRANCE_GRID, style),
        coordinator=coordinator,
        grid=FRANCE_GRID,
        style=style,
        storage_root=root,
        version=str(integration.version),
        layer_cache=layer_cache,
    )

    @callback
    def _keep_polling() -> None:
        """Do nothing.

        The integration has no entities, and a coordinator with no listener never
        schedules its next refresh. This listener only keeps the minute poll alive.
        """

    entry.async_on_unload(coordinator.async_add_listener(_keep_polling))
    await coordinator.async_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RadarConfigEntry) -> bool:
    """Stop polling. Stored frames and cached layers stay on disk."""
    return True


async def async_remove_entry(hass: HomeAssistant, entry: RadarConfigEntry) -> None:
    """Drop the expiring-key issue; the stored history is kept for a reinstall."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_KEY_EXPIRING)
