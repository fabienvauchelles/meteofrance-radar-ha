"""Coordinator running one collector pass every minute.

A missed slot is lost for good (the API only serves the latest product), so the poll
interval is well under the 5-minute product cadence and the catalogue's
``validity_time`` saves the download when nothing changed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .collector import Collector, CollectorState
from .const import DOMAIN, LOGGER, POLL_INTERVAL
from .errors import ApiAuthError, ApiError
from .keyexpiry import async_check_key_expiry

if TYPE_CHECKING:
    from .runtime import RadarConfigEntry


class RadarCoordinator(DataUpdateCoordinator[CollectorState]):
    """Drives the collector; an auth failure starts reauth and stops polling.

    Every pass first reads the key's JWT ``exp`` claim: 14 days ahead it raises the
    expiring-key repair issue, and once the key has expired it starts reauth without
    calling the API.
    """

    config_entry: RadarConfigEntry

    def __init__(self, hass: HomeAssistant, entry: RadarConfigEntry, collector: Collector) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self._collector = collector

    async def _async_update_data(self) -> CollectorState:
        now = dt_util.utcnow()
        async_check_key_expiry(self.hass, self.config_entry, now)
        try:
            return await self._collector.run_pass(now)
        except ApiAuthError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except ApiError as exc:
            raise UpdateFailed(str(exc)) from exc
        except OSError as exc:
            raise UpdateFailed(f"storage error: {type(exc).__name__}: {exc}") from exc
