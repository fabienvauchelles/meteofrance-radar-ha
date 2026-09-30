"""Scenarios for the forecast part of the frames answer and the forecast layer view.

Three PIAF runs are committed one after the other before setup, the way the collector
leaves them: the oldest is gone, the middle one stays as the previous run. Radar
frames are tiny; the forecast APIs answer "not published" so setup fetches nothing.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from PIL import Image
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.meteofrance_radar.domain.forecast import PIAF_LEADS_MIN, PiafRun, PiafStep
from custom_components.meteofrance_radar.domain.grid import FRANCE_GRID
from custom_components.meteofrance_radar.domain.models import AcrrFrame, Scaling, SourceGrid
from custom_components.meteofrance_radar.domain.palette import style_id
from custom_components.meteofrance_radar.store.forecast_store import FileForecastStore
from custom_components.meteofrance_radar.store.frame_store import FileFrameStore
from tests.support.mf_api import SUSPENDED_BODY, mock_catalogue_error
from tests.support.setup import async_setup_integration

NOW = datetime(2026, 9, 30, 15, 8, tzinfo=UTC)
RUNS = [datetime(2026, 9, 30, 14, m, tzinfo=UTC) for m in (15, 30, 45)]
OLDEST, PREVIOUS, CURRENT = RUNS
FRAMES_URL = "/api/meteofrance_radar/frames"
FORECAST_URL = "/api/meteofrance_radar/forecast"
PIN_SERIES_URL = "/api/meteofrance_radar/pin_series"
IMMUTABLE = "private, max-age=31536000, immutable"
TINY_GRID = SourceGrid(
    projdef="+proj=stere +lat_0=90 +lon_0=0 +lat_ts=45 +ellps=WGS84 +datum=WGS84",
    xsize=4,
    ysize=4,
    xscale=500.0,
    yscale=500.0,
    corners=(("UL", 0.0, 1.0), ("UR", 1.0, 1.0), ("LL", 0.0, 0.0), ("LR", 1.0, 0.0)),
)
TINY_SCALING = Scaling(gain=0.01, offset=0.0, nodata=65535.0, undetect=65534.0)


def _stamp(t: datetime) -> str:
    return t.strftime("%Y%m%dT%H%MZ")


def _png(run: datetime, lead: int) -> bytes:
    """A small PNG unique to a run and step, so answers can be told apart."""
    buffer = io.BytesIO()
    Image.new("L", (2, 2), color=(run.minute + lead) % 256).save(buffer, format="PNG")
    return buffer.getvalue()


def _seed(root: Path, radar_until: datetime) -> None:
    """Radar frames every 5 min from 14:00 to `radar_until`, then three PIAF runs."""
    frames = FileFrameStore(root)
    slot = datetime(2026, 9, 30, 14, 0, tzinfo=UTC)
    while slot <= radar_until:
        raw = np.full((4, 4), 65534, dtype=np.uint16)
        frames.write(AcrrFrame(slot=slot, grid=TINY_GRID, scaling=TINY_SCALING, raw=raw))
        slot += timedelta(minutes=5)
    style = style_id(FRANCE_GRID)
    store = FileForecastStore(root)
    store.load(style)
    for run in RUNS:
        store.begin_run(run)
        steps = []
        for lead in PIAF_LEADS_MIN:
            valid = run + timedelta(minutes=lead)
            store.stage_layer(run, valid, _png(run, lead))
            steps.append(PiafStep(valid=valid, lead_min=lead, pin_mm_h=None))
        store.commit_run(PiafRun(run=run, style=style, steps=tuple(steps), pin=None))


async def _load(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    root: Path,
    radar_until: datetime,
) -> None:
    await hass.async_add_executor_job(_seed, root, radar_until)
    mock_catalogue_error(aioclient_mock, HTTPStatus.INTERNAL_SERVER_ERROR, SUSPENDED_BODY)
    await async_setup_integration(hass, root)
    # The first forecast tick runs as a background task of the entry.
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.fixture
def frozen(freezer: FrozenDateTimeFactory) -> None:
    """Freeze the clock before any token is issued."""
    freezer.move_to(NOW)


async def _forecast(client: Any, period: str = "3h") -> dict[str, Any]:
    resp = await client.get(f"{FRAMES_URL}?period={period}")
    assert resp.status == HTTPStatus.OK
    body: dict[str, Any] = await resp.json()
    forecast: dict[str, Any] = body["forecast"]
    return {**forecast, "style": body["style"]}


def _layer_url(style: str, run: datetime, valid: datetime) -> str:
    return f"{FORECAST_URL}/{style}/{_stamp(run)}/{_stamp(valid)}.png"


async def test_forecast_frames_follow_the_latest_radar_slot(
    hass: HomeAssistant,
    tmp_path: Path,
    frozen: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path, datetime(2026, 9, 30, 15, 0, tzinfo=UTC))
    client = await hass_client()
    forecast = await _forecast(client)
    style = forecast["style"]

    # The radar slot of 15:00 is 8 minutes old: it is "now", and the forecast starts after it.
    assert forecast["status"] == "ok"
    assert forecast["source"] == "piaf"
    assert forecast["run"] == "2026-09-30T14:45:00Z"
    assert forecast["now"] == "2026-09-30T15:00:00Z"
    frames = forecast["frames"]
    assert len(frames) == 17
    assert frames[0] == {
        "time": "2026-09-30T15:05:00Z",
        "lead_min": 5,
        "url": _layer_url(style, CURRENT, datetime(2026, 9, 30, 15, 5, tzinfo=UTC)),
    }
    assert [f["lead_min"] for f in frames[8:10]] == [45, 60]
    assert frames[-1]["time"] == "2026-09-30T17:45:00Z"
    assert frames[-1]["lead_min"] == 165
    times = [f["time"] for f in frames]
    assert times == sorted(times)

    # Every period gets the same forecast part.
    long_period = await _forecast(client, "24h")
    assert long_period["frames"] == frames


async def test_stale_radar_leaves_now_on_the_clock(
    hass: HomeAssistant,
    tmp_path: Path,
    frozen: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path, datetime(2026, 9, 30, 14, 25, tzinfo=UTC))
    forecast = await _forecast(await hass_client())
    # The latest frame (14:25) is 43 minutes old, so "now" is the clock floored to 15:05.
    assert forecast["now"] == "2026-09-30T15:05:00Z"
    frames = forecast["frames"]
    assert len(frames) == 16
    assert frames[0]["time"] == "2026-09-30T15:10:00Z"
    assert frames[0]["lead_min"] == 5
    assert frames[-1]["lead_min"] == 160


async def test_forecast_layers_and_refusals(
    hass: HomeAssistant,
    tmp_path: Path,
    frozen: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path, datetime(2026, 9, 30, 15, 0, tzinfo=UTC))
    client = await hass_client()
    forecast = await _forecast(client)
    style = forecast["style"]
    url = forecast["frames"][0]["url"]

    resp = await client.get(url)
    assert resp.status == HTTPStatus.OK
    assert resp.headers["Content-Type"] == "image/png"
    assert resp.headers["Cache-Control"] == IMMUTABLE
    assert await resp.read() == _png(CURRENT, 20)

    # A card that listed the frames just before the last commit still loads them.
    previous_step = PREVIOUS + timedelta(minutes=30)
    resp = await client.get(_layer_url(style, PREVIOUS, previous_step))
    assert resp.status == HTTPStatus.OK
    assert await resp.read() == _png(PREVIOUS, 30)

    step = CURRENT + timedelta(minutes=20)
    for path in (
        _layer_url(style, OLDEST, OLDEST + timedelta(minutes=20)),
        _layer_url("0000000000", CURRENT, step),
        _layer_url(style, CURRENT, datetime(2026, 9, 30, 23, 0, tzinfo=UTC)),
        f"{FORECAST_URL}/{style}/{_stamp(CURRENT)}/20260930T1505.png",
        f"{FORECAST_URL}/{style}/{_stamp(CURRENT)}/20260930T1507Z.png",
        f"{FORECAST_URL}/{style}/2026-09-30T14.45Z/{_stamp(step)}.png",
        f"{FORECAST_URL}/{style}/{_stamp(CURRENT)}/{_stamp(step)}.grib2",
    ):
        assert (await client.get(path)).status == HTTPStatus.NOT_FOUND, path

    anonymous = await hass_client_no_auth()
    assert (await anonymous.get(url)).status == HTTPStatus.UNAUTHORIZED
    assert (await anonymous.get(PIN_SERIES_URL)).status == HTTPStatus.UNAUTHORIZED

    entry = hass.config_entries.async_entries("meteofrance_radar")[0]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert (await client.get(url)).status == HTTPStatus.SERVICE_UNAVAILABLE
    assert (await client.get(FRAMES_URL)).status == HTTPStatus.SERVICE_UNAVAILABLE
    assert (await client.get(PIN_SERIES_URL)).status == HTTPStatus.SERVICE_UNAVAILABLE
