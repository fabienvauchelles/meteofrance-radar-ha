"""Key expiry (repair issue, fix flow, reauth), diagnostics, and the key never reaching a log."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.meteofrance_radar.const import CONF_API_KEY, DOMAIN, ISSUE_KEY_EXPIRING
from tests.support.mf_api import (
    CATALOGUE_URL,
    FIXTURE_SLOT,
    VALID_KEY,
    calls_to,
    dry_product,
    make_key,
    mock_api,
    mock_catalogue_error,
)
from tests.support.setup import NOW, async_setup_integration, async_tick

NEW_KEY = make_key(datetime(2028, 1, 1, tzinfo=UTC), "renewed")


@pytest.fixture(autouse=True)
def _frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(NOW)


def _reauth_flows(hass: HomeAssistant) -> list[str]:
    return [
        flow["flow_id"]
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"]["source"] == SOURCE_REAUTH
    ]


async def test_expiring_key_raises_an_issue_whose_fix_renews_the_key(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    tmp_path: Path,
) -> None:
    expiring = make_key(dt_util.utcnow() + timedelta(days=10))
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, tmp_path / "radar", key=expiring)

    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING)
    assert issue is not None
    assert issue.is_fixable
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders == {"expiry": "2026-10-10"}
    assert _reauth_flows(hass) == []

    assert await async_setup_component(hass, "repairs", {})
    client = await hass_client()
    response = await client.post(
        "/api/repairs/issues/fix", json={"handler": DOMAIN, "issue_id": ISSUE_KEY_EXPIRING}
    )
    assert response.status == HTTPStatus.OK
    flow = await response.json()
    assert flow["step_id"] == "confirm"
    response = await client.post(f"/api/repairs/issues/fix/{flow['flow_id']}", json={})
    assert response.status == HTTPStatus.OK
    assert (await response.json())["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    [reauth] = _reauth_flows(hass)
    result = await hass.config_entries.flow.async_configure(reauth, {CONF_API_KEY: NEW_KEY})
    await hass.async_block_till_done()

    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == NEW_KEY
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING) is None


async def test_issue_appears_when_the_key_enters_the_warning_window(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    key = make_key(dt_util.utcnow() + timedelta(days=14, minutes=1))
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    await async_setup_integration(hass, tmp_path / "radar", key=key)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING) is None

    await async_tick(hass, freezer)

    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING) is not None


async def test_expired_key_starts_reauth_without_calling_the_api(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))

    await async_setup_integration(
        hass, tmp_path / "radar", key=make_key(dt_util.utcnow() - timedelta(minutes=1))
    )

    assert len(_reauth_flows(hass)) == 1
    assert calls_to(aioclient_mock, CATALOGUE_URL) == 0
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING) is None


async def test_key_expiring_while_running_warns_then_reauths_then_resumes(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    key = make_key(dt_util.utcnow() + timedelta(minutes=1, seconds=30))
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, tmp_path / "radar", key=key)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING)
    assert issue is not None
    assert issue.translation_placeholders == {"expiry": "2026-09-30"}
    calls_at_setup = calls_to(aioclient_mock, CATALOGUE_URL)

    await async_tick(hass, freezer)
    assert _reauth_flows(hass) == []
    calls_before_expiry = calls_to(aioclient_mock, CATALOGUE_URL)
    assert calls_before_expiry > calls_at_setup

    await async_tick(hass, freezer)
    await async_tick(hass, freezer)
    await async_tick(hass, freezer)

    [reauth] = _reauth_flows(hass)
    assert calls_to(aioclient_mock, CATALOGUE_URL) == calls_before_expiry
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING) is None
    assert entry.runtime_data.coordinator.last_update_success is False

    result = await hass.config_entries.flow.async_configure(reauth, {CONF_API_KEY: NEW_KEY})
    await hass.async_block_till_done()
    assert result["reason"] == "reauth_successful"
    assert entry.state is ConfigEntryState.LOADED
    assert calls_to(aioclient_mock, CATALOGUE_URL) > calls_before_expiry
    assert entry.runtime_data.coordinator.last_update_success is True
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_KEY_EXPIRING) is None


async def test_diagnostics_redact_the_key_and_describe_the_storage(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    tmp_path: Path,
) -> None:
    root = tmp_path / "radar"
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(hass, root)

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["entry"]["data"] == {CONF_API_KEY: "**REDACTED**"}
    assert diagnostics["key_expiry"] == "2027-09-30T00:00:00Z"
    assert diagnostics["collector"]["outcome"] == "stored"
    assert diagnostics["collector"]["last_stored_slot"] == "2026-09-30T10:30:00Z"
    storage = diagnostics["storage"]
    assert diagnostics["render"]["tables"] == 0
    assert storage["root"] == str(root)
    assert storage["frames"] == 1
    assert storage["frames_per_tier"] == {"5min": 1}
    assert storage["frames_per_kind"] == {"acrr_u16": 1}
    assert storage["latest"] == "2026-09-30T10:30:00Z"
    assert VALID_KEY not in json.dumps(diagnostics)


async def test_diagnostics_of_an_entry_waiting_for_its_storage(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    tmp_path: Path,
) -> None:
    blocker = tmp_path / "not-a-folder"
    blocker.write_bytes(b"")
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    entry = await async_setup_integration(
        hass, blocker / "radar", expect=ConfigEntryState.SETUP_RETRY
    )

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["entry"]["state"] == str(ConfigEntryState.SETUP_RETRY)
    assert diagnostics["entry"]["data"] == {CONF_API_KEY: "**REDACTED**"}
    assert "storage" not in diagnostics
    assert calls_to(aioclient_mock, CATALOGUE_URL) == 0


async def test_the_key_never_reaches_the_logs(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    mock_api(aioclient_mock, FIXTURE_SLOT, b"not an HDF5 file")
    entry = await async_setup_integration(hass, tmp_path / "radar")
    mock_catalogue_error(aioclient_mock, HTTPStatus.INTERNAL_SERVER_ERROR, {"code": "303001"})
    await async_tick(hass, freezer)
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))
    await async_tick(hass, freezer)
    mock_catalogue_error(aioclient_mock, HTTPStatus.UNAUTHORIZED)
    await async_tick(hass, freezer)
    await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert len(_reauth_flows(hass)) == 1
    assert "Error fetching" in caplog.text
    assert "Authentication failed" in caplog.text
    assert VALID_KEY not in caplog.text
    assert VALID_KEY.split(".")[1] not in caplog.text
