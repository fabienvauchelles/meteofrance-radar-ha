"""Forecast failures never touch the radar: refused keys, outages, bad GRIB2, no home."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

import numpy as np
import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meteofrance_radar.const import DOMAIN, PORTAL_URL
from custom_components.meteofrance_radar.domain.forecast import ForecastProduct, ProductStatus
from custom_components.meteofrance_radar.runtime import RadarConfigEntry
from tests.support.forecast_api import (
    ForecastApi,
    dry_piaf_grib,
    forecast_api,
    forecast_call_count,
    mock_forecast_forbidden,
    wcs_calls,
)
from tests.support.grib_factory import write_grib2
from tests.support.mf_api import (
    FIXTURE_SLOT,
    VALID_KEY,
    dry_product,
    make_key,
    mock_api,
    mock_catalogue_error,
)
from tests.support.setup import async_setup_integration, async_tick, frame_files

START = "2026-09-30T15:03:00+00:00"
PIAF = ForecastProduct.PIAF
AROMEPI = ForecastProduct.AROMEPI
AROME = ForecastProduct.AROME
PIAF_ISSUE = "forecast_forbidden_piaf"


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 30, hour, minute, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(START)


@pytest.fixture
def api(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> Iterator[ForecastApi]:
    hass.config.latitude, hass.config.longitude = 48.80, 2.46
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    fake = forecast_api(aioclient_mock)
    fake[PIAF].grib = lambda _run, _valid: dry_piaf_grib()
    yield fake


def status(entry: RadarConfigEntry, product: ForecastProduct) -> ProductStatus:
    return entry.runtime_data.forecast.coordinator.data.of(product).status


def reauth_flows(hass: HomeAssistant) -> int:
    return sum(
        1
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"]["source"] == SOURCE_REAUTH
    )


async def test_refused_piaf_raises_an_issue_until_the_key_is_accepted(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    root = tmp_path / "radar"
    mock_forecast_forbidden(aioclient_mock, PIAF)
    api[AROMEPI].publish(utc(14))

    entry = await async_setup_integration(hass, root)

    assert len(frame_files(root)) == 1
    assert status(entry, PIAF) is ProductStatus.FORBIDDEN
    assert status(entry, AROMEPI) is ProductStatus.OK
    issue = ir.async_get(hass).async_get_issue(DOMAIN, PIAF_ISSUE)
    assert issue is not None
    assert not issue.is_fixable
    assert issue.learn_more_url == PORTAL_URL
    assert issue.translation_key == "forecast_forbidden"
    assert issue.translation_placeholders == {
        "product": "PIAF",
        "api": "Modèle AROME Prévision Immédiate Agrégée Fusionnée (PIAF)",
    }
    refused = len(wcs_calls(aioclient_mock, PIAF))

    await async_tick(hass, freezer, timedelta(minutes=30))
    assert len(wcs_calls(aioclient_mock, PIAF)) == refused
    assert ir.async_get(hass).async_get_issue(DOMAIN, PIAF_ISSUE) is not None

    api[PIAF].status = None
    api[PIAF].publish(utc(15, 45))
    await async_tick(hass, freezer, timedelta(minutes=31))

    assert status(entry, PIAF) is ProductStatus.OK
    assert entry.runtime_data.forecast.store.current_piaf().run == utc(15, 45)
    assert ir.async_get(hass).async_get_issue(DOMAIN, PIAF_ISSUE) is None


async def test_an_outage_backs_off_then_recovers(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    api[AROMEPI].publish(utc(14))
    api[AROMEPI].status = HTTPStatus.INTERNAL_SERVER_ERROR
    entry = await async_setup_integration(hass, tmp_path / "radar")
    state = entry.runtime_data.forecast.coordinator.data.of(AROMEPI)
    assert state.status is ProductStatus.ERROR
    assert state.next_check == dt_util.utcnow() + timedelta(minutes=2)
    assert "HTTP 500" in (state.last_error or "")
    assert ir.async_get(hass).async_get_issue(DOMAIN, "forecast_forbidden_aromepi") is None

    attempts = []
    for _ in range(7):
        await async_tick(hass, freezer)
        attempts.append(len(wcs_calls(aioclient_mock, AROMEPI)))
    # Failed at 15:03, retried at 15:05 (then 4 min later, 15:09).
    assert attempts == [1, 2, 2, 2, 2, 3, 3]

    api[AROMEPI].status = None
    await async_tick(hass, freezer, timedelta(minutes=8))

    assert status(entry, AROMEPI) is ProductStatus.OK
    assert len(wcs_calls(aioclient_mock, AROMEPI, "GetCoverage")) == 24
    assert len(frame_files(tmp_path / "radar")) == 1


async def test_an_unsupported_grib_is_an_error_and_nothing_is_committed(
    hass: HomeAssistant, api: ForecastApi, tmp_path: Path
) -> None:
    root = tmp_path / "radar"
    bitmap = write_grib2(np.zeros((106, 166)), lon0=-6.0, lat0=51.5, dlon=0.1, dlat=0.1, bitmap=0)
    api[PIAF].grib = lambda _run, _valid: bitmap
    api[PIAF].publish(utc(14, 45))

    entry = await async_setup_integration(hass, root)

    state = entry.runtime_data.forecast.coordinator.data.of(PIAF)
    assert state.status is ProductStatus.ERROR
    assert "GribFormatError" in (state.last_error or "")
    assert entry.runtime_data.forecast.store.current_piaf() is None
    assert list((root / "forecast" / "piaf").glob("2026*")) == []
    assert len(frame_files(root)) == 1
    assert entry.runtime_data.coordinator.last_update_success


async def test_an_expired_key_makes_no_forecast_request(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    api[PIAF].publish(utc(14, 45))
    key = make_key(dt_util.utcnow() - timedelta(minutes=1))

    entry = await async_setup_integration(hass, tmp_path / "radar", key=key)
    await async_tick(hass, freezer)

    assert reauth_flows(hass) == 1
    assert forecast_call_count(aioclient_mock) == 0
    assert status(entry, PIAF) is ProductStatus.PENDING


async def test_a_radar_reauth_stops_forecast_requests(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    api[PIAF].publish(utc(14, 45))
    mock_catalogue_error(aioclient_mock, HTTPStatus.UNAUTHORIZED)

    await async_setup_integration(hass, tmp_path / "radar")
    await async_tick(hass, freezer)
    await async_tick(hass, freezer)

    assert reauth_flows(hass) == 1
    assert forecast_call_count(aioclient_mock) == 0


async def test_without_a_home_only_the_maps_are_fetched(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, api: ForecastApi, tmp_path: Path
) -> None:
    hass.config.latitude, hass.config.longitude = 0.0, 0.0
    api[PIAF].publish(utc(14, 45))
    api[AROMEPI].publish(utc(14))
    api[AROME].publish(utc(12), tuple(3600 * h for h in range(1, 11)))

    entry = await async_setup_integration(hass, tmp_path / "radar")

    assert status(entry, AROMEPI) is ProductStatus.OUTSIDE
    assert status(entry, AROME) is ProductStatus.OUTSIDE
    assert wcs_calls(aioclient_mock, AROMEPI) == []
    assert wcs_calls(aioclient_mock, AROME) == []
    assert len(wcs_calls(aioclient_mock, PIAF, "GetCoverage")) == 20
    piaf = entry.runtime_data.forecast.store.current_piaf()
    assert piaf is not None and piaf.pin is None
    assert {step.pin_mm_h for step in piaf.steps} == {None}


async def test_neither_the_key_nor_the_home_reach_the_logs(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    mock_forecast_forbidden(aioclient_mock, PIAF)
    api[AROMEPI].publish(utc(14))
    api[AROMEPI].status = HTTPStatus.INTERNAL_SERVER_ERROR
    api[AROME].publish(utc(12), tuple(3600 * h for h in range(1, 11)))
    await async_setup_integration(hass, tmp_path / "radar")
    api[AROMEPI].status = None
    await async_tick(hass, freezer, timedelta(minutes=3))

    assert "forecast aromepi is now error" in caplog.text.lower()
    assert "forecast piaf is now forbidden" in caplog.text.lower()
    assert VALID_KEY not in caplog.text
    assert VALID_KEY.split(".")[1] not in caplog.text
    for text in ("48.8", "2.46", "2.445", "2.475", "48.785", "48.815"):
        assert text not in caplog.text
