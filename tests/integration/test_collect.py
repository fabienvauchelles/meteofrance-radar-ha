"""Collector passes driven by the coordinator clock, against a mocked DPRadar API."""

from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meteofrance_radar.collector import PassOutcome
from custom_components.meteofrance_radar.const import DOMAIN
from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.domain.models import AcrrFrame
from custom_components.meteofrance_radar.runtime import RadarConfigEntry
from tests.support.mf_api import (
    CATALOGUE_URL,
    FIXTURE_SLOT,
    PRODUCT_URL,
    SUSPENDED_BODY,
    calls_to,
    dry_product,
    mock_api,
    mock_catalogue_error,
)
from tests.support.setup import (
    NOW,
    async_setup_integration,
    async_tick,
    files_with_suffix,
    frame_files,
)

NEXT_SLOT = FIXTURE_SLOT + timedelta(minutes=5)


@pytest.fixture(autouse=True)
def _frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(NOW)


def _outcome(entry: RadarConfigEntry) -> PassOutcome:
    return entry.runtime_data.coordinator.data.outcome


async def test_setup_stores_the_real_product_and_never_the_hdf5(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path, product_bytes: bytes
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, product_bytes)

    entry = await async_setup_integration(hass, root)

    assert _outcome(entry) is PassOutcome.STORED
    [stored] = frame_files(root)
    assert stored.name == "20260930T1030Z.mfr"
    assert stored.stat().st_size < len(product_bytes)
    assert files_with_suffix(tmp_path, ".h5") == []
    assert [p for p in root.rglob("*") if p.is_file() and p.suffix != ".mfr"] == []
    frame = await hass.async_add_executor_job(entry.runtime_data.store.read, FIXTURE_SLOT)
    assert isinstance(frame, AcrrFrame)
    original = read_product(product_bytes)
    assert (frame.raw == original.raw).all()


async def test_unchanged_validity_downloads_nothing(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, tmp_path / "radar")
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))

    await async_tick(hass, freezer)
    await async_tick(hass, freezer)

    assert calls_to(aioclient_mock, CATALOGUE_URL) == 2
    assert calls_to(aioclient_mock, PRODUCT_URL) == 0
    assert _outcome(entry) is PassOutcome.UNCHANGED


async def test_transient_suspension_recovers_on_the_next_tick(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, root)
    coordinator = entry.runtime_data.coordinator

    mock_catalogue_error(aioclient_mock, HTTPStatus.INTERNAL_SERVER_ERROR, SUSPENDED_BODY)
    await async_tick(hass, freezer)
    assert coordinator.last_update_success is False
    assert entry.state is ConfigEntryState.LOADED

    mock_api(aioclient_mock, NEXT_SLOT, dry_product(NEXT_SLOT))
    await async_tick(hass, freezer)

    assert coordinator.last_update_success is True
    assert _outcome(entry) is PassOutcome.STORED
    assert [p.name for p in frame_files(root)] == ["20260930T1030Z.mfr", "20260930T1035Z.mfr"]


async def test_refused_key_starts_reauth_and_stops_polling(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, tmp_path / "radar")

    mock_catalogue_error(aioclient_mock, HTTPStatus.UNAUTHORIZED)
    await async_tick(hass, freezer)
    await async_tick(hass, freezer)
    await async_tick(hass, freezer)

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]
    assert calls_to(aioclient_mock, CATALOGUE_URL) == 1
    assert entry.state is ConfigEntryState.LOADED


async def test_invalid_product_writes_nothing_and_keeps_polling(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, b"<html>not an HDF5 file</html>")

    entry = await async_setup_integration(hass, root)

    assert _outcome(entry) is PassOutcome.FAILED
    assert entry.runtime_data.coordinator.data.last_error is not None
    assert frame_files(root) == []

    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    await async_tick(hass, freezer)

    assert _outcome(entry) is PassOutcome.STORED
    assert len(frame_files(root)) == 1


async def test_a_slot_already_stored_is_skipped(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, root)
    [stored] = frame_files(root)
    written = stored.stat().st_mtime_ns

    # The catalogue already announces 10:35 while the product is still 10:30.
    mock_api(aioclient_mock, NEXT_SLOT, dry_product(FIXTURE_SLOT))
    await async_tick(hass, freezer)

    assert _outcome(entry) is PassOutcome.SKIPPED
    assert frame_files(root) == [stored]
    assert stored.stat().st_mtime_ns == written
    assert "stale validity_time=20260930T1035Z slot=20260930T1030Z" in caplog.text


async def test_low_free_space_skips_the_write(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    nearly_full = SimpleNamespace(total=10**12, used=10**12 - 10**6, free=10**6)

    with patch(
        "custom_components.meteofrance_radar.collector.shutil.disk_usage",
        return_value=nearly_full,
    ):
        entry = await async_setup_integration(hass, root)

    assert _outcome(entry) is PassOutcome.SKIPPED_DISK
    assert frame_files(root) == []
    assert "not written" in caplog.text
