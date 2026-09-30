"""Scenarios for the rain bar series at the home, through an authenticated HTTP client.

The archive holds synthetic radar frames over the last three hours on a small crop of
the real 500 m grid around the home: a wet cell, a nodata cell, an undetect cell. A
PIAF run and the AROME-PI and AROME pin series are committed before setup, read at the
home. The forecast APIs answer "not published" (or refuse PIAF), so setup changes none.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from itertools import pairwise
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pyproj import Transformer
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.meteofrance_radar.domain.forecast import (
    PIAF_LEADS_MIN,
    ForecastProduct,
    PiafRun,
    PiafStep,
    PinSeries,
    PinValue,
)
from custom_components.meteofrance_radar.domain.grid import FRANCE_GRID
from custom_components.meteofrance_radar.domain.models import (
    AcrrFrame,
    ClassFrame,
    Scaling,
    SourceGrid,
)
from custom_components.meteofrance_radar.domain.palette import LEVELS_MMH, style_id
from custom_components.meteofrance_radar.domain.pin_series import class_of
from custom_components.meteofrance_radar.store.forecast_store import FileForecastStore
from custom_components.meteofrance_radar.store.frame_store import FileFrameStore
from tests.support.forecast_api import mock_forecast_forbidden
from tests.support.mf_api import SUSPENDED_BODY, mock_catalogue_error
from tests.support.odim_factory import CELL_M, REAL_CORNERS, REAL_PROJDEF, source_cell
from tests.support.setup import async_setup_integration

NOW = datetime(2026, 9, 30, 15, 7, tzinfo=UTC)
HOME = (48.80, 2.46)
MOVED_HOME = (48.80, 2.48)
URL = "/api/meteofrance_radar/pin_series"
CROP = 16
SCALING = Scaling(gain=0.01, offset=0.0, nodata=65535.0, undetect=65534.0)
WET_RAW = 100  # 1 mm in 5 minutes, 12 mm/h
RADAR_AT_HOME = {
    datetime(2026, 9, 30, 12, 10, tzinfo=UTC): 0,
    datetime(2026, 9, 30, 13, 0, tzinfo=UTC): WET_RAW,
    datetime(2026, 9, 30, 14, 0, tzinfo=UTC): 65535,
    datetime(2026, 9, 30, 14, 55, tzinfo=UTC): 65534,
    datetime(2026, 9, 30, 15, 0, tzinfo=UTC): WET_RAW,
    datetime(2026, 9, 30, 15, 5, tzinfo=UTC): WET_RAW,
}
CLASS_SLOT = datetime(2026, 9, 30, 13, 30, tzinfo=UTC)
PIAF_RUN = datetime(2026, 9, 30, 14, 45, tzinfo=UTC)
AROMEPI_RUN = datetime(2026, 9, 30, 14, 0, tzinfo=UTC)
AROME_RUN = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _crop_grid(lat: float, lon: float) -> tuple[SourceGrid, tuple[int, int]]:
    """A CROP x CROP piece of the real source grid, and the home cell in it."""
    forward = Transformer.from_crs("EPSG:4326", REAL_PROJDEF, always_xy=True)
    inverse = Transformer.from_crs(REAL_PROJDEF, "EPSG:4326", always_xy=True)
    row, col = source_cell(lon, lat)
    r0, c0 = row - CROP // 2, col - CROP // 2
    x_ul, y_ul = forward.transform(*REAL_CORNERS["UL"])
    left, top = x_ul + c0 * CELL_M, y_ul - r0 * CELL_M
    right, bottom = left + CROP * CELL_M, top - CROP * CELL_M
    corners: list[tuple[str, float, float]] = []
    for name, x, y in (
        ("UL", left, top),
        ("UR", right, top),
        ("LL", left, bottom),
        ("LR", right, bottom),
    ):
        lon_c, lat_c = inverse.transform(x, y)
        corners.append((name, float(lon_c), float(lat_c)))
    grid = SourceGrid(REAL_PROJDEF, CROP, CROP, CELL_M, CELL_M, tuple(corners))
    return grid, (row - r0, col - c0)


def _seed_radar(root: Path) -> None:
    grid, (row, col) = _crop_grid(*HOME)
    store = FileFrameStore(root)
    for slot, value in RADAR_AT_HOME.items():
        raw = np.zeros((CROP, CROP), dtype=np.uint16)
        raw[row, col] = value
        store.write(AcrrFrame(slot=slot, grid=grid, scaling=SCALING, raw=raw))
    idx = np.full((CROP, CROP), 5, dtype=np.uint8)
    store.write(ClassFrame(slot=CLASS_SLOT, grid=grid, levels_mmh=LEVELS_MMH, idx=idx))


def _piaf_rate(lead: int) -> float | None:
    if lead == PIAF_LEADS_MIN[-1]:
        return None
    return 0.6 if lead <= 60 else 3.0


def _seed_forecasts(root: Path, *, piaf: bool) -> None:
    lat, lon = HOME
    style = style_id(FRANCE_GRID)
    store = FileForecastStore(root)
    store.load(style)
    if piaf:
        store.begin_run(PIAF_RUN)
        steps = []
        for lead in PIAF_LEADS_MIN:
            valid = PIAF_RUN + timedelta(minutes=lead)
            store.stage_layer(PIAF_RUN, valid, b"png")
            steps.append(PiafStep(valid=valid, lead_min=lead, pin_mm_h=_piaf_rate(lead)))
        store.commit_run(PiafRun(PIAF_RUN, style, tuple(steps), (lon, lat)))
    quarters = [AROMEPI_RUN + timedelta(minutes=15 * i) for i in range(1, 25)]
    hours = [AROME_RUN + timedelta(hours=i) for i in range(1, 11)]
    for product, run, times, rate in (
        (ForecastProduct.AROMEPI, AROMEPI_RUN, quarters, 0.43),
        (ForecastProduct.AROME, AROME_RUN, hours, 0.18),
    ):
        values = tuple(PinValue(valid=t, mm_h=rate) for t in times)
        store.save_pin_series(PinSeries(product, run, lon, lat, values))


async def _load(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, root: Path, *, piaf: bool = True
) -> None:
    """Seed, set the home, set up; without a committed PIAF run, the PIAF API refuses the key."""

    def seed() -> None:
        _seed_radar(root)
        _seed_forecasts(root, piaf=piaf)

    await hass.async_add_executor_job(seed)
    hass.config.latitude, hass.config.longitude = HOME
    mock_catalogue_error(aioclient_mock, HTTPStatus.INTERNAL_SERVER_ERROR, SUSPENDED_BODY)
    if not piaf:
        mock_forecast_forbidden(aioclient_mock, ForecastProduct.PIAF)
    await async_setup_integration(hass, root)
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.fixture
def frozen(freezer: FrozenDateTimeFactory) -> None:
    """Freeze the clock before any token is issued."""
    freezer.move_to(NOW)


@pytest.fixture
def late_evening(freezer: FrozenDateTimeFactory) -> None:
    """Freeze the clock at 22:30 Paris time, before any token is issued."""
    freezer.move_to(datetime(2026, 9, 30, 20, 30, tzinfo=UTC))


async def _series(client: Any) -> dict[str, Any]:
    resp = await client.get(URL)
    assert resp.status == HTTPStatus.OK
    body: dict[str, Any] = await resp.json()
    return body


def _assert_well_formed(segments: list[dict[str, Any]]) -> None:
    for before, after in pairwise(segments):
        assert before["end"] <= after["start"], (before, after)
    for segment in segments:
        assert segment["start"] < segment["end"]
        assert segment["class"] == class_of(segment["mm_h"])


def _sources(segments: list[dict[str, Any]]) -> list[str]:
    return [s["source"] for s in segments]


async def test_bar_joins_radar_piaf_aromepi_and_arome(
    hass: HomeAssistant,
    tmp_path: Path,
    frozen: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path)
    client = await hass_client()
    with patch.object(
        FileFrameStore, "read", autospec=True, side_effect=FileFrameStore.read
    ) as reads:
        body = await _series(client)
        assert reads.call_count == len(RADAR_AT_HOME)
        reads.reset_mock()
        assert await _series(client) == body
        assert reads.call_count == 0

    assert body["version"] == "0.2.0"
    assert body["now"] == "2026-09-30T15:07:00Z"
    # 22:00 UTC is midnight in Paris (summer time), more than 6 hours ahead.
    assert body["window"] == {"start": "2026-09-30T12:07:00Z", "end": "2026-09-30T22:00:00Z"}
    assert body["located"] is True
    assert body["legend"]["unit"] == "mm/h"
    assert body["attribution"] == "Météo-France"
    assert body["sources"]["radar"] == {"status": "ok", "latest": "2026-09-30T15:05:00Z"}
    assert body["sources"]["piaf"]["run"] == "2026-09-30T14:45:00Z"
    assert body["sources"]["aromepi"]["run"] == "2026-09-30T14:00:00Z"
    assert body["sources"]["arome"]["run"] == "2026-09-30T12:00:00Z"

    segments = body["segments"]
    _assert_well_formed(segments)
    assert _sources(segments) == ["radar"] * 6 + ["piaf"] * 15 + ["aromepi"] * 10 + ["arome"] * 2
    radar = segments[:6]
    assert radar[0] == {
        "source": "radar",
        "start": "2026-09-30T12:07:00Z",
        "end": "2026-09-30T12:10:00Z",
        "mm_h": 0.0,
        "class": 0,
    }
    assert [s["mm_h"] for s in radar] == [0.0, 12.0, None, 0.0, 12.0, 12.0]
    assert radar[2] == {**radar[2], "start": "2026-09-30T13:55:00Z", "class": 11}
    piaf = segments[6:21]
    assert piaf[0]["start"] == "2026-09-30T15:05:00Z"
    assert piaf[0]["end"] == "2026-09-30T15:10:00Z"
    assert piaf[8] == {**piaf[8], "start": "2026-09-30T15:45:00Z", "end": "2026-09-30T16:00:00Z"}
    assert {s["mm_h"] for s in piaf} == {0.6, 3.0}
    assert segments[21]["start"] == piaf[-1]["end"] == "2026-09-30T17:30:00Z"
    assert segments[21]["mm_h"] == 0.43
    assert segments[-1] == {
        "source": "arome",
        "start": "2026-09-30T21:00:00Z",
        "end": "2026-09-30T22:00:00Z",
        "mm_h": 0.18,
        "class": class_of(0.18),
    }


async def test_late_evening_bar_reaches_six_hours_ahead(
    hass: HomeAssistant,
    tmp_path: Path,
    late_evening: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    # 22:30 in Paris: midnight is closer than six hours, so the window ends at +6 h.
    await _load(hass, aioclient_mock, tmp_path)
    body = await _series(await hass_client())
    assert body["window"] == {"start": "2026-09-30T17:30:00Z", "end": "2026-10-01T02:30:00Z"}
    # Setup thinned the archive to hourly frames: 15:00 keeps its hour.
    assert body["sources"]["radar"] == {"status": "stale", "latest": "2026-09-30T15:00:00Z"}
    segments = body["segments"]
    _assert_well_formed(segments)
    assert segments[0]["start"] == "2026-09-30T17:30:00Z"
    assert _sources(segments) == ["aromepi"] * 10 + ["arome"] * 2


async def test_home_moved_or_unset(
    hass: HomeAssistant,
    tmp_path: Path,
    frozen: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path)
    client = await hass_client()
    assert len((await _series(client))["segments"]) == 33

    # Forecasts were read at the old home: only the radar remains, read at the new cell.
    hass.config.latitude, hass.config.longitude = MOVED_HOME
    moved = await _series(client)
    assert moved["located"] is True
    assert _sources(moved["segments"]) == ["radar"] * 6
    assert {s["mm_h"] for s in moved["segments"]} == {0.0}

    hass.config.latitude, hass.config.longitude = 0.0, 0.0
    unset = await _series(client)
    assert unset["located"] is False
    assert unset["segments"] == []
    assert unset["window"]["end"] == "2026-09-30T22:00:00Z"


async def test_piaf_forbidden_lets_aromepi_start_at_the_radar_end(
    hass: HomeAssistant,
    tmp_path: Path,
    frozen: None,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path, piaf=False)
    body = await _series(await hass_client())
    segments = body["segments"]
    _assert_well_formed(segments)
    assert body["sources"]["piaf"] == {"status": "forbidden", "run": None}
    assert _sources(segments)[:7] == ["radar"] * 6 + ["aromepi"]
    assert segments[6]["start"] == segments[5]["end"] == "2026-09-30T15:05:00Z"
    assert segments[6]["end"] == "2026-09-30T15:15:00Z"
    assert _sources(segments)[-2:] == ["arome", "arome"]
