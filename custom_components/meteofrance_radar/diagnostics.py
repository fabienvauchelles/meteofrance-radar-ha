"""Diagnostics: entry settings with the key redacted, collector state, storage and forecasts.

The forecast section never holds the home location, pin values or request URLs.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api.apikey import api_key_expiry
from .const import CONF_API_KEY
from .domain.forecast import ForecastProduct, ProductState
from .domain.slots import format_iso
from .domain.tiers import tier_of
from .forecast_issues import active_forecast_issues
from .runtime import ForecastRuntime, RadarConfigEntry

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
        "forecast": await _forecast_section(hass, runtime.forecast, runtime.style),
    }


def _iso(t: datetime | None) -> str | None:
    return format_iso(t) if t is not None else None


def _product_section(state: ProductState | None, requests: int) -> dict[str, Any]:
    return {
        "status": str(state.status) if state else None,
        "run": _iso(state.run) if state else None,
        "last_success": _iso(state.last_success) if state else None,
        "last_error": state.last_error if state else None,
        "next_check": _iso(state.next_check) if state else None,
        "requests_last_minute": requests,
    }


async def _forecast_section(
    hass: HomeAssistant, forecast: ForecastRuntime, style: str
) -> dict[str, Any]:
    data = forecast.coordinator.data
    piaf = await hass.async_add_executor_job(forecast.store.current_piaf)
    return {
        "products": {
            str(product): _product_section(
                data.of(product) if data else None,
                forecast.clients[product].requests_last_minute,
            )
            for product in ForecastProduct
        },
        "piaf_steps": len(piaf.steps) if piaf else 0,
        "piaf_style_ok": piaf.style == style if piaf else None,
        "forecast_bytes": await hass.async_add_executor_job(forecast.store.total_bytes),
        "issues": active_forecast_issues(hass),
    }
