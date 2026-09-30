"""Scenarios for the frames and layer views, through an authenticated HTTP client.

The archive is seeded on disk before the entry is set up, so the views see it through
the index the integration loads at setup. Seeded frames are tiny except the one real
product the layer scenarios render. The Météo-France API answers "suspended" so the
setup pass stores nothing new.
"""

from __future__ import annotations

import io
import math
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from PIL import Image
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.domain.models import AcrrFrame, Scaling, SourceGrid
from custom_components.meteofrance_radar.domain.slots import format_iso
from custom_components.meteofrance_radar.render import service as render_service
from custom_components.meteofrance_radar.store.frame_store import FileFrameStore
from tests.conftest import PRODUCT_FIXTURE
from tests.support.mf_api import SUSPENDED_BODY, mock_catalogue_error
from tests.support.setup import async_setup_integration

NOW = datetime(2026, 9, 30, 10, 33, tzinfo=UTC)
LATEST = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)
FIVE_MIN_GAP = {datetime(2026, 9, 30, 9, m, tzinfo=UTC) for m in (0, 5, 10)}
MISSING_HOUR = datetime(2026, 9, 29, 12, tzinfo=UTC)
OLD_SLOTS = [datetime(2026, 8, 20, h, tzinfo=UTC) for h in (0, 3, 6)]
SPARSE_HOURS = [datetime(2026, 9, 10, tzinfo=UTC), datetime(2026, 9, 25, tzinfo=UTC)]
FRAMES_URL = "/api/meteofrance_radar/frames"
LAYERS_URL = "/api/meteofrance_radar/layers"
IMMUTABLE = "private, max-age=31536000, immutable"
PARIS = (48.8566, 2.3522)
TINY_GRID = SourceGrid(
    projdef="+proj=stere +lat_0=90 +lon_0=0 +lat_ts=45 +ellps=WGS84 +datum=WGS84",
    xsize=4,
    ysize=4,
    xscale=500.0,
    yscale=500.0,
    corners=(("UL", 0.0, 1.0), ("UR", 1.0, 1.0), ("LL", 0.0, 0.0), ("LR", 1.0, 0.0)),
)
type Seeder = Callable[[Path], None]
TINY_SCALING = Scaling(gain=0.01, offset=0.0, nodata=65535.0, undetect=65534.0)


def _five_min_slots() -> list[datetime]:
    first = datetime(2026, 9, 30, 7, 35, tzinfo=UTC)
    slots = [first + timedelta(minutes=5 * i) for i in range(36)]
    return [s for s in slots if s not in FIVE_MIN_GAP]


def _hourly_slots() -> list[datetime]:
    first = datetime(2026, 9, 29, tzinfo=UTC)
    slots = [first + timedelta(hours=i) for i in range(32)]
    return [s for s in slots if s != MISSING_HOUR]


def _seed(storage: Path, slots: Iterable[datetime]) -> None:
    store = FileFrameStore(storage)
    for slot in slots:
        raw = np.full((4, 4), 65534, dtype=np.uint16)
        store.write(AcrrFrame(slot=slot, grid=TINY_GRID, scaling=TINY_SCALING, raw=raw))


def _layer_name(t: datetime) -> str:
    return t.strftime("%Y%m%dT%H%MZ") + ".png"


def _mercator_pixel(lat: float, lon: float) -> tuple[float, float]:
    """Web Mercator pixel of FRANCE_GRID, computed here from its published parameters."""
    radius = 6378137.0
    res = 2 * math.pi * radius / 256 / 2**6.4

    def xy(lo: float, la: float) -> tuple[float, float]:
        return radius * math.radians(lo), radius * math.log(
            math.tan(math.pi / 4 + math.radians(la) / 2)
        )

    x, y = xy(lon, lat)
    xc, yc = xy(2.5, 46.6)
    return (x - xc) / res + 960, 540 - (y - yc) / res


@pytest.fixture
def frozen(freezer: FrozenDateTimeFactory) -> None:
    """Freeze the clock before any token is issued, or the token would be from the future."""
    freezer.move_to(NOW)


async def _load(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, storage: Path, seed: Seeder
) -> None:
    await hass.async_add_executor_job(seed, storage)
    mock_catalogue_error(aioclient_mock, HTTPStatus.INTERNAL_SERVER_ERROR, SUSPENDED_BODY)
    await async_setup_integration(hass, storage)


@pytest.fixture
async def archive(
    hass: HomeAssistant, tmp_path: Path, frozen: None, aioclient_mock: AiohttpClientMocker
) -> Path:
    """A loaded entry over an archive spanning every tier, with deliberate holes."""
    slots = [*OLD_SLOTS, *SPARSE_HOURS, *_hourly_slots(), *_five_min_slots()]
    await _load(hass, aioclient_mock, tmp_path, lambda root: _seed(root, slots))
    return tmp_path


async def _frames(client: Any, period: str) -> dict[str, Any]:
    resp = await client.get(f"{FRAMES_URL}?period={period}")
    assert resp.status == HTTPStatus.OK
    body: dict[str, Any] = await resp.json()
    return body


async def test_three_hours_skips_the_hole_and_counts_it(
    hass: HomeAssistant, archive: Path, hass_client: ClientSessionGenerator
) -> None:
    client = await hass_client()
    body = await _frames(client, "3h")
    assert body["version"] == "0.2.0"
    assert body["grid"] == {
        "width": 1920,
        "height": 1080,
        "center_lon": 2.5,
        "center_lat": 46.6,
        "zoom": 6.4,
    }
    assert body["basemap"] == "/meteofrance_radar/basemap.png?v=0.2.0"
    assert body["attribution"]["radar"] == "Météo-France"
    assert body["legend"]["unit"] == "mm/h"
    assert len(body["legend"]["levels"]) == len(body["legend"]["colors"]) + 1
    assert body["period"] == {
        "name": "3h",
        "from": "2026-09-30T07:35:00Z",
        "to": "2026-09-30T10:35:00Z",
    }
    assert body["latest"] == format_iso(LATEST)
    assert body["oldest"] == format_iso(OLD_SLOTS[0])
    frames = body["frames"]
    assert [f["time"] for f in frames] == [format_iso(s) for s in _five_min_slots()]
    assert {f["tier"] for f in frames} == {"5min"}
    gaps = {f["time"]: f["gap_before_min"] for f in frames if f["gap_before_min"]}
    assert gaps == {"2026-09-30T09:15:00Z": 20}
    assert body["missing"] == 3
    forecast: dict[str, Any] = {"status": "pending", "source": "piaf", "run": None, "frames": []}
    assert body["forecast"] == {**forecast, "now": format_iso(LATEST)}
    last = frames[-1]
    assert last["url"] == f"{LAYERS_URL}/{body['style']}/{_layer_name(LATEST)}"
    assert (await client.get(FRAMES_URL)).status == HTTPStatus.OK


async def test_day_mixes_hourly_and_five_minute_frames(
    hass: HomeAssistant, archive: Path, hass_client: ClientSessionGenerator
) -> None:
    body = await _frames(await hass_client(), "24h")
    assert body["period"]["from"] == "2026-09-29T10:35:00Z"
    frames = body["frames"]
    assert frames[0] == {
        **frames[0],
        "time": "2026-09-29T11:00:00Z",
        "tier": "1h",
        "gap_before_min": 0,
    }
    assert len(frames) == 20 + 33
    gaps = {f["time"]: f["gap_before_min"] for f in frames if f["gap_before_min"]}
    assert gaps == {"2026-09-29T13:00:00Z": 120, "2026-09-30T09:15:00Z": 20}
    tiers = {f["time"]: f["tier"] for f in frames}
    assert tiers["2026-09-30T07:00:00Z"] == "1h"
    assert tiers["2026-09-30T07:35:00Z"] == "5min"
    assert body["missing"] == 4


@pytest.mark.parametrize(
    ("period", "start", "count"),
    [
        ("7d", "2026-09-23T10:35:00Z", 65),
        ("30d", "2026-08-31T10:35:00Z", 66),
        ("all", "2026-08-20T00:00:00Z", 69),
    ],
)
async def test_longer_periods_reach_back_through_the_tiers(
    hass: HomeAssistant,
    archive: Path,
    hass_client: ClientSessionGenerator,
    period: str,
    start: str,
    count: int,
) -> None:
    body = await _frames(await hass_client(), period)
    assert body["period"] == {"name": period, "from": start, "to": "2026-09-30T10:35:00Z"}
    assert len(body["frames"]) == count
    assert body["missing"] > 0
    if period == "all":
        assert [f["tier"] for f in body["frames"][:3]] == ["3h", "3h", "3h"]


async def test_pin_follows_the_home_location(
    hass: HomeAssistant, archive: Path, hass_client: ClientSessionGenerator
) -> None:
    client = await hass_client()
    hass.config.latitude, hass.config.longitude = PARIS
    pin = (await _frames(client, "3h"))["pin"]
    x, y = _mercator_pixel(*PARIS)
    assert pin["inside"] is True
    assert pin["x"] == pytest.approx(x, abs=0.06)
    assert pin["y"] == pytest.approx(y, abs=0.06)

    hass.config.latitude, hass.config.longitude = 32.87, -117.22
    assert (await _frames(client, "3h"))["pin"]["inside"] is False

    hass.config.latitude, hass.config.longitude = 0.0, 0.0
    assert (await _frames(client, "3h"))["pin"] is None


async def test_refusals_bad_period_no_token_and_no_loaded_entry(
    hass: HomeAssistant,
    archive: Path,
    hass_client: ClientSessionGenerator,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    client = await hass_client()
    resp = await client.get(f"{FRAMES_URL}?period=2h")
    assert resp.status == HTTPStatus.BAD_REQUEST
    assert "2h" in (await resp.json())["error"]
    layer_url = f"{LAYERS_URL}/{(await _frames(client, '3h'))['style']}/{_layer_name(LATEST)}"
    anonymous = await hass_client_no_auth()
    assert (await anonymous.get(FRAMES_URL)).status == HTTPStatus.UNAUTHORIZED
    assert (await anonymous.get(layer_url)).status == HTTPStatus.UNAUTHORIZED

    entry = hass.config_entries.async_entries("meteofrance_radar")[0]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert (await client.get(FRAMES_URL)).status == HTTPStatus.SERVICE_UNAVAILABLE
    assert (await client.get(layer_url)).status == HTTPStatus.SERVICE_UNAVAILABLE


def _seed_real_product(storage: Path) -> None:
    FileFrameStore(storage).write(read_product(PRODUCT_FIXTURE.read_bytes()))


async def test_layer_renders_once_then_comes_from_the_cache(
    hass: HomeAssistant,
    tmp_path: Path,
    frozen: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path, _seed_real_product)
    client = await hass_client()
    frames = (await _frames(client, "3h"))["frames"]
    assert len(frames) == 1
    url = frames[0]["url"]

    with patch.object(
        render_service, "render_layer", wraps=render_service.render_layer
    ) as renderer:
        first = await client.get(url)
        assert first.status == HTTPStatus.OK
        assert first.headers["Content-Type"] == "image/png"
        assert first.headers["Cache-Control"] == IMMUTABLE
        png = await first.read()
        second = await client.get(url)
        assert second.status == HTTPStatus.OK
        assert await second.read() == png
    assert renderer.call_count == 1
    assert Image.open(io.BytesIO(png)).size == (1920, 1080)


async def test_layer_404_and_500_cases(
    hass: HomeAssistant, archive: Path, hass_client: ClientSessionGenerator
) -> None:
    client = await hass_client()
    style = (await _frames(client, "3h"))["style"]
    for path in (
        f"{LAYERS_URL}/0000000000/{_layer_name(LATEST)}",
        f"{LAYERS_URL}/{style}/20260930T1030.png",
        f"{LAYERS_URL}/{style}/20260930T1032Z.png",
        f"{LAYERS_URL}/{style}/{_layer_name(datetime(2026, 9, 30, 9, 0, tzinfo=UTC))}",
    ):
        assert (await client.get(path)).status == HTTPStatus.NOT_FOUND, path

    frame_file = FileFrameStore(archive).path_for(LATEST)
    data = frame_file.read_bytes()
    frame_file.write_bytes(data[:-8] + bytes(8))
    resp = await client.get(f"{LAYERS_URL}/{style}/{_layer_name(LATEST)}")
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert await resp.json() == {"error": "cannot render layer", "slot": "20260930T1030Z"}
