"""Diagnostics: entry settings with the key redacted, collector state and storage stats."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api.apikey import api_key_expiry
from .const import CONF_API_KEY
from .domain.slots import format_iso
from .domain.tiers import tier_of
from .runtime import RadarConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RadarConfigEntry
) -> dict[str, Any]:
    """Return the diagnostics of the entry; runtime sections only once it is loaded."""
    expiry = api_key_expiry(entry.data[CONF_API_KEY])
    summary: dict[str, Any] = {
        "entry": {
            "state": str(entry.state),
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "key_expiry": format_iso(expiry) if expiry else None,
    }
    if entry.state is not ConfigEntryState.LOADED:
        return summary
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    now = dt_util.utcnow()
    entries = runtime.store.entries()
    layer_bytes = await hass.async_add_executor_job(runtime.layer_cache.total_bytes)
    state = coordinator.data
    last_exception = coordinator.last_exception
    return {
        **summary,
        "collector": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                f"{type(last_exception).__name__}: {last_exception}" if last_exception else None
            ),
            "last_pass": format_iso(state.last_pass) if state else None,
            "outcome": str(state.outcome) if state else None,
            "last_stored_slot": (
                format_iso(state.last_stored_slot) if state and state.last_stored_slot else None
            ),
            "last_error": state.last_error if state else None,
        },
        "render": {
            "style": runtime.style,
            "grid": runtime.grid.key(),
            "version": runtime.version,
            "tables": runtime.layers.table_count,
        },
        "storage": {
            "root": str(runtime.storage_root),
            "frames": len(entries),
            "frames_per_tier": dict(Counter(str(tier_of(e.slot, now)) for e in entries)),
            "frames_per_kind": dict(Counter(str(e.kind) for e in entries)),
            "frame_bytes": sum(e.size for e in entries),
            "layer_bytes": layer_bytes,
            "oldest": format_iso(entries[0].slot) if entries else None,
            "latest": format_iso(entries[-1].slot) if entries else None,
        },
    }
