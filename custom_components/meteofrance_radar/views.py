"""HTTP views the card reads: the frame list of a period and the rendered layers.

Both views need a Home Assistant token (``requires_auth`` stays True); the card
calls them through ``hass.callApi`` and ``hass.fetchWithAuth``. They are
registered once per process and find the loaded entry on each request, so they
answer 503 while no entry is loaded instead of disappearing.
"""

from __future__ import annotations

import re
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER, URL_FRAMES, URL_LAYERS
from .domain.slots import format_slot, parse_slot
from .errors import (
    FrameFormatError,
    InvalidProductError,
    PeriodError,
    SlotNotFoundError,
    StyleNotFoundError,
)
from .http.frames import HomeLocation, build_frames_payload

if TYPE_CHECKING:
    from .runtime import RadarRuntime

LAYER_NAME: Final = re.compile(r"^(\d{8}T\d{4}Z)\.png$")
LAYER_CACHE_CONTROL: Final = "private, max-age=31536000, immutable"
PNG_CONTENT_TYPE: Final = "image/png"
PERIOD_PARAM: Final = "period"
RENDER_FAILED: Final = "cannot render layer"
# Slots whose render failure was already logged in full; later failures log at debug.
MAX_REPORTED_FAILURES: Final = 256


@callback
def async_register_views(hass: HomeAssistant) -> None:
    """Register the frames and layer views. Called once from ``async_setup``."""
    hass.http.register_view(FramesView())
    hass.http.register_view(LayerView())


def _runtime(hass: HomeAssistant) -> RadarRuntime | None:
    """Runtime data of the loaded entry, None when no entry is loaded."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        return None
    runtime: RadarRuntime = entries[0].runtime_data
    return runtime


def _error(message: str, status: HTTPStatus, **extra: Any) -> web.Response:
    return HomeAssistantView.json({"error": message, **extra}, status)


def _home_location(hass: HomeAssistant) -> HomeLocation | None:
    """HA's home coordinates, None when the instance has no location set.

    Home Assistant stores an unset location as (0, 0), a point in the Gulf of
    Guinea no home is at.
    """
    lat, lon = hass.config.latitude, hass.config.longitude
    if lat == 0 and lon == 0:
        return None
    return HomeLocation(lat=lat, lon=lon)


class FramesView(HomeAssistantView):
    """GET the frames of a period, read from the in-memory frame index only."""

    url = URL_FRAMES
    name = f"api:{DOMAIN}:frames"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Answer the frame list of the requested period (default 3 h)."""
        hass = request.app[KEY_HASS]
        runtime = _runtime(hass)
        if runtime is None:
            return _error("the integration is not loaded", HTTPStatus.SERVICE_UNAVAILABLE)
        try:
            payload = build_frames_payload(
                period_name=request.query.get(PERIOD_PARAM),
                entries=runtime.store.entries(),
                now=dt_util.utcnow(),
                grid=runtime.grid,
                style=runtime.style,
                version=runtime.version,
                home=_home_location(hass),
            )
        except PeriodError as err:
            return _error(err.message, HTTPStatus.BAD_REQUEST)
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
        runtime = _runtime(hass)
        if runtime is None:
            return _error("the integration is not loaded", HTTPStatus.SERVICE_UNAVAILABLE)
        match = LAYER_NAME.match(name)
        if match is None:
            return _error(f"not a layer name: {name}", HTTPStatus.NOT_FOUND)
        try:
            slot = parse_slot(match.group(1))
        except ValueError:
            return _error(f"not a slot: {name}", HTTPStatus.NOT_FOUND)
        try:
            png = await hass.async_add_executor_job(runtime.layers.get_layer, style, slot)
        except StyleNotFoundError:
            return _error(f"unknown style: {style}", HTTPStatus.NOT_FOUND)
        except SlotNotFoundError:
            return _error(f"no frame for slot {format_slot(slot)}", HTTPStatus.NOT_FOUND)
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
    return _error(RENDER_FAILED, HTTPStatus.INTERNAL_SERVER_ERROR, slot=format_slot(slot))
