"""Layer view scenarios around rendering: downgraded history, failures and table memory.

Each scenario seeds the archive on disk, sets the entry up with the Météo-France API
answering "suspended", then asks for layers through an authenticated HTTP client.
"""

from __future__ import annotations

import io
import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from numpy.typing import NDArray
from PIL import Image
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.decode.reproject import DEFAULT_MAX_TABLES
from custom_components.meteofrance_radar.domain.models import (
    AcrrFrame,
    ClassFrame,
    Scaling,
    SourceGrid,
)
from custom_components.meteofrance_radar.domain.palette import LEVELS_MMH, NODATA_INDEX
from custom_components.meteofrance_radar.render import service as render_service
from custom_components.meteofrance_radar.store.frame_store import FileFrameStore
from tests.support.mf_api import SUSPENDED_BODY, dry_product, mock_catalogue_error
from tests.support.setup import async_setup_integration

NOW = datetime(2026, 9, 30, 10, 33, tzinfo=UTC)
FRAMES_URL = "/api/meteofrance_radar/frames"
LAYERS_URL = "/api/meteofrance_radar/layers"
OLD_SLOT = datetime(2026, 8, 20, 0, tzinfo=UTC)
CURRENT_SLOT = datetime(2026, 8, 20, 3, tzinfo=UTC)
LATEST = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)
# Levels of an older palette: its class 1 starts at 4 mm/h, today's class 5.
OLD_LEVELS = (4.0, 6.0, 10.0, 16.0, 25.0, 40.0, 70.0, 100.0, 150.0, 200.0, 300.0)
OLD_CLASS, OLD_CLASS_TODAY = 1, 5
VIEWS_MODULE = "views"
SECRET = "/very/private/path/and/stack"
DRY_SCALING = Scaling(gain=0.01, offset=0.0, nodata=65535.0, undetect=65534.0)
type Seeder = Callable[[Path], None]


@pytest.fixture(autouse=True)
def _frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(NOW)


def _product_grid() -> SourceGrid:
    return read_product(dry_product(LATEST)).grid


def _name(slot: datetime) -> str:
    return slot.strftime("%Y%m%dT%H%MZ") + ".png"


def _indices(png: bytes) -> NDArray[np.uint8]:
    with Image.open(io.BytesIO(png)) as image:
        return np.asarray(image)


async def _load(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, storage: Path, seed: Seeder
) -> Any:
    await hass.async_add_executor_job(seed, storage)
    mock_catalogue_error(aioclient_mock, HTTPStatus.INTERNAL_SERVER_ERROR, SUSPENDED_BODY)
    return await async_setup_integration(hass, storage)


async def _style(client: Any) -> str:
    resp = await client.get(f"{FRAMES_URL}?period=all")
    assert resp.status == HTTPStatus.OK
    style: str = (await resp.json())["style"]
    return style


def _seed_downgraded(storage: Path) -> None:
    grid = _product_grid()
    shape = (grid.ysize, grid.xsize)
    store = FileFrameStore(storage)
    for slot, levels in ((OLD_SLOT, OLD_LEVELS), (CURRENT_SLOT, LEVELS_MMH)):
        idx = np.full(shape, OLD_CLASS, dtype=np.uint8)
        store.write(ClassFrame(slot=slot, grid=grid, levels_mmh=levels, idx=idx))


async def test_downgraded_frames_render_with_their_own_levels(
    hass: HomeAssistant,
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    await _load(hass, aioclient_mock, tmp_path, _seed_downgraded)
    client = await hass_client()
    style = await _style(client)

    old = await client.get(f"{LAYERS_URL}/{style}/{_name(OLD_SLOT)}")
    current = await client.get(f"{LAYERS_URL}/{style}/{_name(CURRENT_SLOT)}")

    assert old.status == HTTPStatus.OK
    assert current.status == HTTPStatus.OK
    old_idx, current_idx = _indices(await old.read()), _indices(await current.read())
    covered = current_idx != NODATA_INDEX
    assert covered.mean() > 0.5
    assert set(np.unique(current_idx[covered])) == {OLD_CLASS}
    assert set(np.unique(old_idx[covered])) == {OLD_CLASS_TODAY}
    assert np.array_equal(old_idx == NODATA_INDEX, ~covered)


def _seed_latest(storage: Path) -> None:
    FileFrameStore(storage).write(read_product(dry_product(LATEST)))


async def test_unexpected_render_error_answers_a_clean_500_and_logs_once(
    hass: HomeAssistant,
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await _load(hass, aioclient_mock, tmp_path, _seed_latest)
    client = await hass_client()
    url = f"{LAYERS_URL}/{await _style(client)}/{_name(LATEST)}"

    with patch.object(render_service, "render_layer", side_effect=RuntimeError(SECRET)):
        responses = [await client.get(url) for _ in range(3)]

    for resp in responses:
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
        body = await resp.text()
        assert SECRET not in body
        assert "Traceback" not in body
        assert await resp.json() == {"error": "cannot render layer", "slot": "20260930T1030Z"}
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR and r.module == VIEWS_MODULE]
    assert len(errors) == 1
    assert "20260930T1030Z" in errors[0].getMessage()
    assert errors[0].exc_info is not None

    recovered = await client.get(url)
    assert recovered.status == HTTPStatus.OK


def _grid_variant(grid: SourceGrid, n: int) -> SourceGrid:
    return replace(grid, xscale=grid.xscale + n)


def _seed_many_grids(storage: Path) -> None:
    grid = _product_grid()
    store = FileFrameStore(storage)
    raw = np.full((grid.ysize, grid.xsize), 65534, dtype=np.uint16)
    for hour in range(DEFAULT_MAX_TABLES + 2):
        store.write(
            AcrrFrame(
                slot=datetime(2026, 9, 30, hour, tzinfo=UTC),
                grid=_grid_variant(grid, hour),
                scaling=DRY_SCALING,
                raw=raw,
            )
        )


async def test_reprojection_tables_stay_bounded_across_source_grids(
    hass: HomeAssistant,
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    entry = await _load(hass, aioclient_mock, tmp_path, _seed_many_grids)
    client = await hass_client()
    style = await _style(client)

    for hour in range(DEFAULT_MAX_TABLES + 2):
        slot = datetime(2026, 9, 30, hour, tzinfo=UTC)
        resp = await client.get(f"{LAYERS_URL}/{style}/{_name(slot)}")
        assert resp.status == HTTPStatus.OK

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert diagnostics["render"]["tables"] == DEFAULT_MAX_TABLES
