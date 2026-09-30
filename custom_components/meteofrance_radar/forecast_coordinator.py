"""Coordinator running one forecast tick every minute.

Forecasts are optional: a refused or failing forecast API only changes that product's
status and never fails the update. No forecast request is made while the key has
expired or the radar API refused it (reauth pending): the same key would be refused.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_API_KEY, DOMAIN, FORECAST_POLL_INTERVAL, LOGGER
from .domain.forecast import ForecastState
from .forecast.service import ForecastService
from .forecast_issues import async_sync_forecast_issues
from .keyexpiry import key_is_expired

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import RadarCoordinator


class ForecastCoordinator(DataUpdateCoordinator[ForecastState]):
    """Drives the forecast service and keeps the repair issues in step with it."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        service: ForecastService,
        radar: RadarCoordinator,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} forecast",
            update_interval=FORECAST_POLL_INTERVAL,
        )
        self._service = service
        self._radar = radar

    def api_allowed(self) -> bool:
        """False when the key has expired or the radar API refused it."""
        entry = self.config_entry
        if entry is None or key_is_expired(entry.data[CONF_API_KEY], dt_util.utcnow()):
            return False
        return not isinstance(self._radar.last_exception, ConfigEntryAuthFailed)

    async def _async_update_data(self) -> ForecastState:
        state = await self._service.run_tick(dt_util.utcnow(), api_allowed=self.api_allowed())
        async_sync_forecast_issues(self.hass, state)
        return state
