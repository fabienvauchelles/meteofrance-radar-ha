"""HTTP views for forecasts: PIAF layer PNGs and the rain bar series at the home.

Like the radar views, they need a Home Assistant token, find the loaded entry on each
request and answer 503 while none is loaded. The helpers at the top are shared with
``views.py``, which registers every view.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN, URL_FORECAST_LAYERS, URL_PIN_SERIES
from .domain.forecast import ForecastProduct, ForecastState, PiafRun, PinSeries
from .domain.slots import parse_slot
from .http.frames import HomeLocation
from .http.pin_series import build_pin_series_payload, radar_query_range

if TYPE_CHECKING:
    from .runtime import RadarRuntime

LAYER_NAME: Final = re.compile(r"^(\d{8}T\d{4}Z)\.png$")
LAYER_CACHE_CONTROL: Final = "private, max-age=31536000, immutable"
PNG_CONTENT_TYPE: Final = "image/png"
NOT_LOADED: Final = "the integration is not loaded"


def loaded_runtime(hass: HomeAssistant) -> RadarRuntime | None:
    """Runtime data of the loaded entry, None when no entry is loaded."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        return None
    runtime: RadarRuntime = entries[0].runtime_data
    return runtime


def error_response(message: str, status: HTTPStatus, **extra: Any) -> web.Response:
    """JSON error body {"error": message, ...extra} with the given status."""
    return HomeAssistantView.json({"error": message, **extra}, status)


def home_location(hass: HomeAssistant) -> HomeLocation | None:
    """HA's home coordinates, None when the instance has no location set.

    Home Assistant stores an unset location as (0, 0), a point in the Gulf of
    Guinea no home is at.
    """
    lat, lon = hass.config.latitude, hass.config.longitude
    if lat == 0 and lon == 0:
        return None
    return HomeLocation(lat=lat, lon=lon)


def forecast_state(runtime: RadarRuntime) -> ForecastState | None:
    """Latest forecast states, None before the first forecast tick."""
    state: ForecastState | None = runtime.forecast.coordinator.data
    return state


class ForecastLayerView(HomeAssistantView):
    """GET one PIAF layer PNG of the current or the previous run."""

    url = URL_FORECAST_LAYERS
    name = f"api:{DOMAIN}:forecast_layer"
    requires_auth = True

    async def get(self, request: web.Request, style: str, run: str, name: str) -> web.Response:
        """Answer the PNG with an immutable, private cache header, else 404."""
        hass = request.app[KEY_HASS]
        runtime = loaded_runtime(hass)
        if runtime is None:
            return error_response(NOT_LOADED, HTTPStatus.SERVICE_UNAVAILABLE)
        if style != runtime.style:
            return error_response(f"unknown style: {style}", HTTPStatus.NOT_FOUND)
        match = LAYER_NAME.match(name)
        if match is None:
            return error_response(f"not a layer name: {name}", HTTPStatus.NOT_FOUND)
        try:
            run_time = parse_slot(run)
            valid = parse_slot(match.group(1))
        except ValueError:
            return error_response(f"not a run and step: {run}/{name}", HTTPStatus.NOT_FOUND)
        png = await hass.async_add_executor_job(runtime.forecast.store.read_layer, run_time, valid)
        if png is None:
            return error_response(f"no forecast layer {run}/{name}", HTTPStatus.NOT_FOUND)
        return web.Response(
            body=png,
            content_type=PNG_CONTENT_TYPE,
            headers={"Cache-Control": LAYER_CACHE_CONTROL},
        )


class PinSeriesView(HomeAssistantView):
    """GET the rain bar segments at the home: radar history, then forecasts."""

    url = URL_PIN_SERIES
    name = f"api:{DOMAIN}:pin_series"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Answer the stitched segments of the bar window."""
        hass = request.app[KEY_HASS]
        runtime = loaded_runtime(hass)
        if runtime is None:
            return error_response(NOT_LOADED, HTTPStatus.SERVICE_UNAVAILABLE)
        now = dt_util.utcnow()
        home = home_location(hass)
        entries = runtime.store.entries()
        latest = entries[-1].slot if entries else None
        inputs = await hass.async_add_executor_job(
            _read_pin_inputs, runtime, home, radar_query_range(now, latest)
        )
        payload = build_pin_series_payload(
            now=now,
            version=runtime.version,
            home=home,
            radar=inputs.radar,
            latest=latest,
            piaf=inputs.piaf,
            aromepi=inputs.aromepi,
            arome=inputs.arome,
            state=forecast_state(runtime),
        )
        return self.json(payload)


@dataclass(frozen=True)
class _PinInputs:
    radar: list[tuple[datetime, float | None]]
    piaf: PiafRun | None
    aromepi: PinSeries | None
    arome: PinSeries | None


def _read_pin_inputs(
    runtime: RadarRuntime,
    home: HomeLocation | None,
    span: tuple[datetime, datetime] | None,
) -> _PinInputs:
    """Blocking reads of the pin_series view, run in the executor.

    The forecast store takes its lock around disk writes (staging, commit, pruning),
    so even its in-memory getters can wait on disk and must stay off the event loop.
    """
    forecast = runtime.forecast
    radar: list[tuple[datetime, float | None]] = []
    if home is not None and span is not None:
        radar = forecast.pin_history.values(home.lon, home.lat, *span)
    return _PinInputs(
        radar=radar,
        piaf=forecast.store.current_piaf(),
        aromepi=forecast.store.pin_series(ForecastProduct.AROMEPI),
        arome=forecast.store.pin_series(ForecastProduct.AROME),
    )
