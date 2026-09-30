"""Forecast collection through the forecast coordinator, against faked WCS APIs.

The home is in Paris (48.80 N, 2.46 E), the clock starts at 15:03 UTC. PIAF maps come
from the real 14:50 +30 min GRIB2, pins from the real 3x3 tiny-bbox GRIB2 files.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from yarl import URL

from custom_components.meteofrance_radar.const import FORECAST_MAX_PER_MINUTE
from custom_components.meteofrance_radar.domain.forecast import ForecastProduct, ProductStatus
from custom_components.meteofrance_radar.runtime import RadarConfigEntry
from tests.support.forecast_api import (
    AROME_PIN_MM_H,
    AROMEPI_PIN_MM_H,
    ForecastApi,
    dry_piaf_grib,
    forecast_api,
    valid_time_of,
    wcs_calls,
)
from tests.support.mf_api import FIXTURE_SLOT, VALID_KEY, dry_product, mock_api
from tests.support.setup import async_setup_integration, async_tick, files_with_suffix

START = "2026-09-30T15:03:00+00:00"
HOME_LAT, HOME_LON = 48.80, 2.46
PIAF = ForecastProduct.PIAF
AROMEPI = ForecastProduct.AROMEPI
AROME = ForecastProduct.AROME
GET = "GetCoverage"
DESCRIBE = "DescribeCoverage"


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 30, hour, minute, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(START)


@pytest.fixture
def api(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> Iterator[ForecastApi]:
    hass.config.latitude, hass.config.longitude = HOME_LAT, HOME_LON
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    yield forecast_api(aioclient_mock)


def piaf_dir(root: Path) -> Path:
    return root / "forecast" / "piaf"


def run_dirs(root: Path) -> list[str]:
    return sorted(p.name for p in piaf_dir(root).iterdir() if p.is_dir())


def subsets(url: URL) -> list[str]:
    return url.query.getall("subset", [])


def state_of(entry: RadarConfigEntry, product: ForecastProduct) -> ProductStatus:
    return entry.runtime_data.forecast.coordinator.data.of(product).status


async def tick_until(hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: datetime) -> None:
    while dt_util.utcnow() < when:
        await async_tick(hass, freezer)


async def test_piaf_runs_are_rendered_committed_and_replaced(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    root = tmp_path / "radar"
    api[PIAF].publish(utc(14, 45))

    entry = await async_setup_integration(hass, root)

    gets = wcs_calls(aioclient_mock, PIAF, GET)
    assert len(gets) == 20
    for url, headers in gets:
        assert headers["apikey"] == VALID_KEY
        assert url.query["format"] == "application/wmo-grib"
        times = [s for s in subsets(url) if s.startswith("time(")]
        assert len(times) == 1
        assert {"long(-6,10.5)", "lat(41,51.5)"} <= set(subsets(url))
    valid = [valid_time_of(url) for url, _ in gets]
    assert valid[0] == utc(14, 50) and valid[11] == utc(15, 45) and valid[-1] == utc(17, 45)
    run_dir = piaf_dir(root) / "20260930T1445Z"
    assert len(list(run_dir.glob("*.png"))) == 20
    manifest = json.loads((run_dir / "run.json").read_text())
    assert manifest["pin"] == [HOME_LON, HOME_LAT]
    assert [step["pin_mm_h"] for step in manifest["steps"]] == [0.0] * 20
    assert files_with_suffix(tmp_path, ".grib2") == []
    assert run_dirs(root) == ["20260930T1445Z"]
    assert state_of(entry, PIAF) is ProductStatus.OK

    await tick_until(hass, freezer, utc(15, 8))
    last_describe, _ = wcs_calls(aioclient_mock, PIAF, DESCRIBE)[-1]
    assert "2026-09-30T15.00.00Z" in last_describe.query["coverageID"]
    assert run_dirs(root) == ["20260930T1445Z"]

    api[PIAF].grib = lambda _run, _valid: dry_piaf_grib()
    api[PIAF].publish(utc(15, 0))
    await async_tick(hass, freezer)
    assert run_dirs(root) == ["20260930T1445Z", "20260930T1500Z"]
    assert entry.runtime_data.forecast.store.current_piaf().run == utc(15, 0)

    api[PIAF].publish(utc(15, 15))
    await tick_until(hass, freezer, utc(15, 23))
    assert run_dirs(root) == ["20260930T1500Z", "20260930T1515Z"]
    assert len(wcs_calls(aioclient_mock, PIAF, GET)) == 60


async def test_aromepi_pin_series_comes_from_24_tiny_requests(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, api: ForecastApi, tmp_path: Path
) -> None:
    root = tmp_path / "radar"
    api[AROMEPI].publish(utc(14, 0))

    entry = await async_setup_integration(hass, root)

    gets = wcs_calls(aioclient_mock, AROMEPI, GET)
    assert len(gets) == 24
    for url, headers in gets:
        assert headers["apikey"] == VALID_KEY
        assert {"long(2.445,2.475)", "lat(48.785,48.815)"} <= set(subsets(url))
    saved = json.loads((root / "forecast" / "pins" / "aromepi.json").read_text())
    assert saved["run"] == "2026-09-30T14:00:00Z"
    assert [value[1] for value in saved["values"]] == [AROMEPI_PIN_MM_H] * 24
    assert saved["values"][0][0] == "2026-09-30T14:15:00Z"
    assert state_of(entry, AROMEPI) is ProductStatus.OK


async def test_arome_fetches_only_the_steps_it_does_not_hold(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    root = tmp_path / "radar"
    hourly = tuple(3600 * h for h in range(1, 11))
    api[AROME].publish(utc(12), hourly)

    entry = await async_setup_integration(hass, root)

    first = [valid_time_of(url) for url, _ in wcs_calls(aioclient_mock, AROME, GET)]
    assert first == [utc(h) for h in range(16, 23)]
    store = entry.runtime_data.forecast.store
    series = store.pin_series(AROME)
    assert series is not None and series.run == utc(12)
    assert {value.mm_h for value in series.values} == {AROME_PIN_MM_H}

    await async_tick(hass, freezer)
    assert len(wcs_calls(aioclient_mock, AROME, GET)) == 7

    api[AROME].publish(utc(12), (*hourly, 3600 * 11, 3600 * 12))
    await async_tick(hass, freezer, timedelta(hours=3))

    later = [valid_time_of(url) for url, _ in wcs_calls(aioclient_mock, AROME, GET)][7:]
    assert later == [utc(23), utc(23) + timedelta(hours=1)]
    series = store.pin_series(AROME)
    assert series is not None
    assert [value.valid for value in series.values] == [
        *(utc(h) for h in range(18, 24)),
        utc(23) + timedelta(hours=1),
    ]


async def test_every_api_stays_under_its_minute_budget(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    api[PIAF].grib = lambda _run, _valid: dry_piaf_grib()
    for run in (utc(14, 45), utc(15, 0), utc(15, 15)):
        api[PIAF].publish(run)
    api[AROMEPI].publish(utc(14, 0))
    api[AROMEPI].publish(utc(15, 0))
    api[AROME].publish(utc(12), tuple(3600 * h for h in range(1, 25)))
    entry = await async_setup_integration(hass, tmp_path / "radar")
    per_minute = [{p: len(wcs_calls(aioclient_mock, p)) for p in ForecastProduct}]

    for _ in range(25):
        aioclient_mock.mock_calls.clear()
        await async_tick(hass, freezer)
        per_minute.append({p: len(wcs_calls(aioclient_mock, p)) for p in ForecastProduct})

    assert max(counts[p] for counts in per_minute for p in ForecastProduct) <= (
        FORECAST_MAX_PER_MINUTE
    )
    assert sum(counts[PIAF] for counts in per_minute) >= 60
    assert entry.runtime_data.forecast.store.current_piaf().run == utc(15, 15)
    assert entry.runtime_data.forecast.store.pin_series(AROMEPI).run == utc(15)


async def test_a_restart_reloads_the_forecasts_without_fetching_them_again(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, api: ForecastApi, tmp_path: Path
) -> None:
    api[PIAF].grib = lambda _run, _valid: dry_piaf_grib()
    api[PIAF].publish(utc(14, 45))
    api[AROMEPI].publish(utc(14, 0))
    api[AROME].publish(utc(12), tuple(3600 * h for h in range(1, 11)))
    entry = await async_setup_integration(hass, tmp_path / "radar")
    before = entry.runtime_data.forecast.store
    aioclient_mock.mock_calls.clear()

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    for product in ForecastProduct:
        assert wcs_calls(aioclient_mock, product, GET) == []
    store = entry.runtime_data.forecast.store
    assert store is not before
    piaf = store.current_piaf()
    assert piaf is not None and piaf.run == utc(14, 45) and len(piaf.steps) == 20
    assert store.pin_series(AROMEPI) == before.pin_series(AROMEPI)
    assert store.pin_series(AROME) == before.pin_series(AROME)
    assert state_of(entry, PIAF) is ProductStatus.OK


async def test_arome_jumps_to_the_latest_run_after_a_long_downtime(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    hourly = tuple(3600 * h for h in range(1, 25))
    api[AROME].publish(utc(12), hourly)
    entry = await async_setup_integration(hass, tmp_path / "radar")
    store = entry.runtime_data.forecast.store
    assert store.pin_series(AROME).run == utc(12)
    for hour in (15, 18, 21):
        api[AROME].publish(utc(hour), hourly)

    await async_tick(hass, freezer, timedelta(hours=12))

    series = store.pin_series(AROME)
    assert series is not None and series.run == utc(21)
    assert state_of(entry, AROME) is ProductStatus.OK


async def test_arome_covers_a_window_end_that_is_not_on_the_hour(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api: ForecastApi,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    # At 16:14 UTC the bar ends at 22:14 (6 h ahead, after Paris midnight at 22:00);
    # the 23:00 value covers 22:00-23:00, so the bar needs it to reach its end.
    freezer.move_to("2026-09-30T16:14:00+00:00")
    api[AROME].publish(utc(12), tuple(3600 * h for h in range(1, 13)))

    entry = await async_setup_integration(hass, tmp_path / "radar")

    fetched = [valid_time_of(url) for url, _ in wcs_calls(aioclient_mock, AROME, GET)]
    assert fetched == [utc(h) for h in range(17, 24)]
    series = entry.runtime_data.forecast.store.pin_series(AROME)
    assert series is not None and series.values[-1].valid == utc(23)
