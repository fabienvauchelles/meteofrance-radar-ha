"""Config, reauth, reconfigure and options flows.

Every step that takes a key checks it twice: the JWT ``exp`` claim locally, then a live
catalogue request. Changing the key never touches the frames on disk. The options pick
the storage folder and the size cap; changing the folder does not move old frames.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import dt as dt_util

from .api.client import DPRadarClient
from .const import (
    CONF_API_KEY,
    CONF_SIZE_CAP_MB,
    CONF_STORAGE_PATH,
    DEFAULT_SIZE_CAP_MB,
    DOMAIN,
    MAX_SIZE_CAP_MB,
    MIN_SIZE_CAP_MB,
)
from .errors import ApiAuthError, ApiError, StoragePathError
from .keyexpiry import key_is_expired
from .runtime import RadarConfigEntry, prepare_storage_root, storage_root_of

TITLE = "Météo-France Radar"
KEY_SCHEMA = vol.Schema(
    {vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))}
)


async def validate_key(hass: HomeAssistant, key: str) -> str | None:
    """Check a key locally then live; return an error code, or None when it works."""
    if key_is_expired(key, dt_util.utcnow()):
        return "key_expired"
    client = DPRadarClient(async_get_clientsession(hass), key)
    try:
        await client.latest_validity_time()
    except ApiAuthError:
        return "invalid_auth"
    except ApiError:
        return "cannot_connect"
    return None


class RadarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Collects the API key. One entry only (``single_config_entry`` in the manifest)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_API_KEY].strip()
            error = await validate_key(self.hass, key)
            if error is None:
                return self.async_create_entry(title=TITLE, data={CONF_API_KEY: key})
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=KEY_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_API_KEY].strip()
            error = await validate_key(self.hass, key)
            if error is None:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_API_KEY: key}
                )
            errors["base"] = error
        return self.async_show_form(step_id="reauth_confirm", data_schema=KEY_SCHEMA, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_API_KEY].strip()
            error = await validate_key(self.hass, key)
            if error is None:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(), data_updates={CONF_API_KEY: key}
                )
            errors["base"] = error
        return self.async_show_form(step_id="reconfigure", data_schema=KEY_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: RadarConfigEntry) -> RadarOptionsFlow:
        return RadarOptionsFlow()


class RadarOptionsFlow(OptionsFlowWithReload):
    """Storage folder and size cap; the entry reloads when they change."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            path = Path(user_input[CONF_STORAGE_PATH].strip())
            error = await self._check_path(path)
            if error is None:
                return self.async_create_entry(
                    data={
                        CONF_STORAGE_PATH: str(path),
                        CONF_SIZE_CAP_MB: int(user_input[CONF_SIZE_CAP_MB]),
                    }
                )
            errors[CONF_STORAGE_PATH] = error
        return self.async_show_form(
            step_id="init", data_schema=self._schema(user_input), errors=errors
        )

    async def _check_path(self, path: Path) -> str | None:
        if not path.is_absolute():
            return "path_not_absolute"
        try:
            await self.hass.async_add_executor_job(prepare_storage_root, path)
        except StoragePathError:
            return "path_not_writable"
        return None

    def _schema(self, user_input: Mapping[str, Any] | None) -> vol.Schema:
        options = self.config_entry.options
        path = storage_root_of(self.hass, self.config_entry)
        values = user_input or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_STORAGE_PATH, default=values.get(CONF_STORAGE_PATH, str(path))
                ): TextSelector(),
                vol.Required(
                    CONF_SIZE_CAP_MB,
                    default=values.get(
                        CONF_SIZE_CAP_MB, options.get(CONF_SIZE_CAP_MB, DEFAULT_SIZE_CAP_MB)
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SIZE_CAP_MB,
                        max=MAX_SIZE_CAP_MB,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="MB",
                    )
                ),
            }
        )
