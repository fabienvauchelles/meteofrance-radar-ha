"""Repair flow for the expiring API key: confirming it starts the reauth flow."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ISSUE_KEY_EXPIRING


class KeyExpiringRepairFlow(RepairsFlow):
    """Asks for confirmation, then opens the reauth flow of the entry."""

    def __init__(self, entry_id: str | None) -> None:
        self._entry_id = entry_id

    async def async_step_init(self, user_input: dict[str, str] | None = None) -> RepairsFlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))
        entry = self._entry()
        if entry is None:
            return self.async_abort(reason="entry_not_found")
        entry.async_start_reauth(self.hass)
        return self.async_create_entry(data={})

    def _entry(self) -> ConfigEntry | None:
        if self._entry_id is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry is not None:
                return entry
        entries = self.hass.config_entries.async_entries(DOMAIN)
        return entries[0] if entries else None


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, str | int | float | None] | None
) -> RepairsFlow:
    """Create the fix flow of an issue raised by this integration."""
    if issue_id != ISSUE_KEY_EXPIRING:
        raise ValueError(f"unknown issue {issue_id}")
    entry_id = data.get("entry_id") if data else None
    return KeyExpiringRepairFlow(entry_id if isinstance(entry_id, str) else None)
