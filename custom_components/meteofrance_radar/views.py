"""HTTP views the card reads: the frame list of a period and the rendered layers.

Forecast layers and the rain bar series live in ``views_forecast.py``. Every view needs
a Home Assistant token (``requires_auth`` stays True); the card calls them through
``hass.callApi`` and ``hass.fetchWithAuth``. They are registered once per process and
find the loaded entry on each request, so they answer 503 while no entry is loaded
instead of disappearing.
"""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Final

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER, URL_FRAMES, URL_LAYERS
from .domain.forecast import ForecastProduct
from .domain.slots import format_slot, parse_slot
from .errors import (
    FrameFormatError,
    InvalidProductError,
    PeriodError,
    SlotNotFoundError,
    StyleNotFoundError,
)
from .http.forecast import forecast_payload
from .http.frames import build_frames_payload
from .views_forecast import (
    LAYER_CACHE_CONTROL,
    LAYER_NAME,
    NOT_LOADED,
    PNG_CONTENT_TYPE,
    ForecastLayerView,
    PinSeriesView,
    error_response,
    forecast_state,
    home_location,
    loaded_runtime,
)

PERIOD_PARAM: Final = "period"
RENDER_FAILED: Final = "cannot render layer"
# Slots whose render failure was already logged in full; later failures log at debug.
MAX_REPORTED_FAILURES: Final = 256


@callback
def async_register_views(hass: HomeAssistant) -> None:
    """Register every view of the integration. Called once from ``async_setup``."""
    hass.http.register_view(FramesView())
    hass.http.register_view(LayerView())
    hass.http.register_view(ForecastLayerView())
    hass.http.register_view(PinSeriesView())


class FramesView(HomeAssistantView):
    """GET the frames of a period, read from the in-memory frame index only."""

    url = URL_FRAMES
    name = f"api:{DOMAIN}:frames"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Answer the frame list of the requested period (default 3 h)."""
        hass = request.app[KEY_HASS]
        runtime = loaded_runtime(hass)
        if runtime is None:
            return error_response(NOT_LOADED, HTTPStatus.SERVICE_UNAVAILABLE)
        now = dt_util.utcnow()
        entries = runtime.store.entries()
        state = forecast_state(runtime)
        # The forecast store holds its lock during disk writes: read it off the loop.
        piaf = await hass.async_add_executor_job(runtime.forecast.store.current_piaf)
        forecast = forecast_payload(
            piaf=piaf,
            state=None if state is None else state.of(ForecastProduct.PIAF),
            latest=entries[-1].slot if entries else None,
            now=now,
            style=runtime.style,
        )
        try:
            payload = build_frames_payload(
                period_name=request.query.get(PERIOD_PARAM),
                entries=entries,
                now=now,
                grid=runtime.grid,
                style=runtime.style,
                version=runtime.version,
                home=home_location(hass),
                forecast=forecast,
            )
        except PeriodError as err:
            return error_response(err.message, HTTPStatus.BAD_REQUEST)
        return self.json(payload)


class LayerView(HomeAssistantView):
    """GET one rendered layer PNG, from the cache or rendered in the executor."""

    url = URL_LAYERS
    name = f"api:{DOMAIN}:layer"
    requires_auth = True

    def __init__(self) -> None:
        self._reported: set[datetime] = set()

    async def get(self, request: web.Request, style: str, name: str) -> web.Response:
        """Answer the PNG of a slot with an immutable, private cache header."""
        hass = request.app[KEY_HASS]
        runtime = loaded_runtime(hass)
        if runtime is None:
            return error_response(NOT_LOADED, HTTPStatus.SERVICE_UNAVAILABLE)
        match = LAYER_NAME.match(name)
        if match is None:
            return error_response(f"not a layer name: {name}", HTTPStatus.NOT_FOUND)
        try:
            slot = parse_slot(match.group(1))
        except ValueError:
            return error_response(f"not a slot: {name}", HTTPStatus.NOT_FOUND)
        try:
            png = await hass.async_add_executor_job(runtime.layers.get_layer, style, slot)
        except StyleNotFoundError:
            return error_response(f"unknown style: {style}", HTTPStatus.NOT_FOUND)
        except SlotNotFoundError:
            return error_response(f"no frame for slot {format_slot(slot)}", HTTPStatus.NOT_FOUND)
        except (InvalidProductError, FrameFormatError) as err:
            self._log_failure(slot, "Cannot render the layer of slot %s: %s", err.message)
            return _render_failed(slot)
        except Exception:
            # The card retries a failed layer on every loop: log the traceback once per
            # slot, and never send it to the client.
            self._log_failure(slot, "Unexpected error rendering the layer of slot %s", None)
            return _render_failed(slot)
        return web.Response(
            body=png,
            content_type=PNG_CONTENT_TYPE,
            headers={"Cache-Control": LAYER_CACHE_CONTROL},
        )

    def _log_failure(self, slot: datetime, message: str, detail: str | None) -> None:
        """Log a render failure in full the first time for a slot, at debug afterwards.

        Called from an ``except`` block, so the traceback of the failure is attached.
        """
        args = (format_slot(slot), detail) if detail is not None else (format_slot(slot),)
        if slot in self._reported:
            LOGGER.debug(message, *args, exc_info=True)
            return
        if len(self._reported) >= MAX_REPORTED_FAILURES:
            self._reported.clear()
        self._reported.add(slot)
        if detail is None:
            LOGGER.exception(message, *args)
        else:
            LOGGER.error(message, *args)


def _render_failed(slot: datetime) -> web.Response:
    return error_response(RENDER_FAILED, HTTPStatus.INTERNAL_SERVER_ERROR, slot=format_slot(slot))
