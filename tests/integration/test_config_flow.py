"""Config, reauth, reconfigure and options flows, driven through the flow managers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meteofrance_radar.const import (
    CONF_API_KEY,
    CONF_SIZE_CAP_MB,
    CONF_STORAGE_PATH,
    DOMAIN,
)
from tests.support.mf_api import (
    CATALOGUE_URL,
    FIXTURE_SLOT,
    VALID_KEY,
    api_key_headers,
    calls_to,
    dry_product,
    make_key,
    mock_api,
    mock_catalogue_error,
    mock_catalogue_unreachable,
)
from tests.support.setup import (
    NOW,
    async_setup_integration,
    frame_files,
    radar_entry,
    use_tmp_media,
)

NEW_KEY = make_key(datetime(2028, 1, 1, tzinfo=UTC), "new")


@pytest.fixture(autouse=True)
def _frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(NOW)


async def _start_user_flow(hass: HomeAssistant, key: str) -> config_entries.ConfigFlowResult:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: key})


async def test_user_flow_creates_entry_and_collects(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    root = use_tmp_media(hass, tmp_path)
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))

    result = await _start_user_flow(hass, f"  {VALID_KEY}  ")
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Météo-France Radar"
    assert result["data"] == {CONF_API_KEY: VALID_KEY}
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    assert [path.name for path in frame_files(root)] == ["20260930T1030Z.mfr"]
    assert set(api_key_headers(aioclient_mock)) == {VALID_KEY}


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (HTTPStatus.UNAUTHORIZED, "invalid_auth"),
        (HTTPStatus.FORBIDDEN, "invalid_auth"),
        (HTTPStatus.INTERNAL_SERVER_ERROR, "cannot_connect"),
    ],
)
async def test_user_flow_reports_api_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    status: HTTPStatus,
    error: str,
) -> None:
    use_tmp_media(hass, tmp_path)
    mock_catalogue_error(aioclient_mock, status)

    result = await _start_user_flow(hass, VALID_KEY)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_user_flow_recovers_after_a_timeout(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    use_tmp_media(hass, tmp_path)
    mock_catalogue_unreachable(aioclient_mock)
    result = await _start_user_flow(hass, VALID_KEY)
    assert result["errors"] == {"base": "cannot_connect"}

    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: VALID_KEY}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_refuses_an_expired_key_without_calling_the_api(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    use_tmp_media(hass, tmp_path)
    mock_api(aioclient_mock, FIXTURE_SLOT)

    result = await _start_user_flow(hass, make_key(dt_util.utcnow() - timedelta(days=1)))

    assert result["errors"] == {"base": "key_expired"}
    assert calls_to(aioclient_mock, CATALOGUE_URL) == 0


async def test_second_entry_is_aborted(hass: HomeAssistant, tmp_path: Path) -> None:
    radar_entry(tmp_path / "radar").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_reauth_updates_the_key_and_keeps_the_history(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, root)
    stored = frame_files(root)
    assert len(stored) == 1

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    mock_catalogue_error(aioclient_mock, HTTPStatus.UNAUTHORIZED)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "refused"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: NEW_KEY}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == NEW_KEY
    assert entry.state is ConfigEntryState.LOADED
    assert frame_files(root) == stored
    assert set(api_key_headers(aioclient_mock)) == {NEW_KEY}


async def test_reconfigure_changes_the_key(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, root)

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: make_key(dt_util.utcnow() - timedelta(seconds=1))}
    )
    assert result["errors"] == {"base": "key_expired"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: NEW_KEY}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_API_KEY] == NEW_KEY
    assert entry.state is ConfigEntryState.LOADED
    assert len(frame_files(root)) == 1


async def test_options_move_storage_and_validate_input(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    old_root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, old_root)
    blocker = tmp_path / "a-file"
    blocker.write_text("not a folder")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    for path, error in (
        ("relative/radar", "path_not_absolute"),
        (str(blocker / "radar"), "path_not_writable"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_STORAGE_PATH: path, CONF_SIZE_CAP_MB: 500}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_STORAGE_PATH: error}
    for cap in (99, 100_001):
        with pytest.raises(InvalidData):
            await hass.config_entries.options.async_configure(
                result["flow_id"], {CONF_STORAGE_PATH: str(old_root), CONF_SIZE_CAP_MB: cap}
            )

    new_root = tmp_path / "elsewhere" / "radar"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_STORAGE_PATH: str(new_root), CONF_SIZE_CAP_MB: 2000}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_STORAGE_PATH: str(new_root), CONF_SIZE_CAP_MB: 2000}
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.storage_root == new_root
    assert len(frame_files(old_root)) == 1
    assert len(frame_files(new_root)) == 1
