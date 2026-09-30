"""Runtime objects of a loaded entry, and where its files live.

The storage root sits outside /config by default (``<media>/meteofrance_radar``) so
Home Assistant backups stay small. It survives reauth, reconfigure, reload and
reinstall: nothing in the integration ever deletes it.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_STORAGE_PATH, STORAGE_SUBDIR
from .errors import StoragePathError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .api.wcs import WcsClient
    from .coordinator import RadarCoordinator
    from .domain.forecast import ForecastProduct
    from .domain.grid import TargetGrid
    from .domain.ports import FrameStore, LayerCache
    from .forecast_coordinator import ForecastCoordinator
    from .pinseries.radar_history import RadarPinHistory
    from .render.service import LayerService
    from .store.forecast_store import FileForecastStore

PROBE_PREFIX = ".probe-"
MEDIA_DIR_KEY = "local"


@dataclass
class ForecastRuntime:
    """Forecast side of a loaded entry: stored runs and series, coordinator, pin history."""

    store: FileForecastStore
    coordinator: ForecastCoordinator
    pin_history: RadarPinHistory
    clients: Mapping[ForecastProduct, WcsClient]


@dataclass
class RadarRuntime:
    """Everything a loaded entry shares with the views and diagnostics."""

    store: FrameStore
    layers: LayerService
    coordinator: RadarCoordinator
    grid: TargetGrid
    style: str
    storage_root: Path
    version: str
    layer_cache: LayerCache
    forecast: ForecastRuntime


type RadarConfigEntry = ConfigEntry[RadarRuntime]


def default_storage_root(hass: HomeAssistant) -> Path:
    """``<local media dir>/meteofrance_radar``, falling back to ``<config>/media``."""
    media = hass.config.media_dirs.get(MEDIA_DIR_KEY) or hass.config.path("media")
    return Path(media) / STORAGE_SUBDIR


def storage_root_of(hass: HomeAssistant, entry: ConfigEntry) -> Path:
    """Storage root chosen in the options, else the default one."""
    configured = entry.options.get(CONF_STORAGE_PATH)
    return Path(configured) if configured else default_storage_root(hass)


def prepare_storage_root(root: Path) -> None:
    """Create the storage root if needed and prove it is writable (blocking).

    Raises:
        StoragePathError: the path is relative, cannot be created or cannot be written.
    """
    if not root.is_absolute():
        raise StoragePathError(f"storage path is not absolute: {root}")
    try:
        root.mkdir(parents=True, exist_ok=True)
        handle, probe = tempfile.mkstemp(prefix=PROBE_PREFIX, dir=root)
        os.close(handle)
        os.unlink(probe)
    except OSError as exc:
        raise StoragePathError(
            f"storage path is not writable: {root}", cause=f"{type(exc).__name__}: {exc}"
        ) from exc
