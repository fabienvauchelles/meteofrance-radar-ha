"""Scenarios for the static card files and the card's Lovelace resource.

Lovelace is set up next to the integration, in storage mode unless a scenario asks
for YAML resources. The Météo-France API answers "suspended": these scenarios do not
depend on any stored frame.
"""

from __future__ import annotations

import io
import logging
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from PIL import Image
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.meteofrance_radar.domain.grid import FRANCE_GRID
from custom_components.meteofrance_radar.frontend import async_register_frontend
from tests.support.mf_api import SUSPENDED_BODY, mock_catalogue_error
from tests.support.setup import async_setup_integration

WWW = Path(__file__).parents[2] / "custom_components" / "meteofrance_radar" / "www"
CARD_URL = "/meteofrance_radar/meteofrance-radar-card.js"
BASEMAP_URL = "/meteofrance_radar/basemap.png"
CURRENT = f"{CARD_URL}?v=0.2.0"
RESOURCES_KEY = "lovelace_resources"


def _stored_resources(*urls: str) -> dict[str, Any]:
    items = [{"id": f"r{i}", "type": "module", "url": url} for i, url in enumerate(urls)]
    return {"version": 1, "minor_version": 1, "key": RESOURCES_KEY, "data": {"items": items}}


async def _setup(
    hass: HomeAssistant,
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
    lovelace: dict[str, Any] | None = None,
) -> None:
    assert await async_setup_component(hass, "lovelace", {"lovelace": lovelace or {}})
    mock_catalogue_error(aioclient_mock, HTTPStatus.INTERNAL_SERVER_ERROR, SUSPENDED_BODY)
    await async_setup_integration(hass, tmp_path)


async def _resource_urls(hass: HomeAssistant) -> list[str]:
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    return [str(item["url"]) for item in resources.async_items()]


async def test_card_and_basemap_are_served_statically(
    hass: HomeAssistant,
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    await _setup(hass, tmp_path, aioclient_mock)
    client = await hass_client_no_auth()
    card = await client.get(CURRENT)
    assert card.status == HTTPStatus.OK
    assert await card.read() == (WWW / "meteofrance-radar-card.js").read_bytes()
    basemap = await client.get(f"{BASEMAP_URL}?v=0.2.0")
    assert basemap.status == HTTPStatus.OK
    image = Image.open(io.BytesIO(await basemap.read()))
    assert image.size == (FRANCE_GRID.width, FRANCE_GRID.height) == (1920, 1080)


async def test_resource_is_created_in_storage_mode(
    hass: HomeAssistant, tmp_path: Path, aioclient_mock: AiohttpClientMocker
) -> None:
    await _setup(hass, tmp_path, aioclient_mock)
    assert await _resource_urls(hass) == [CURRENT]
    assert hass.data[LOVELACE_DATA].resources.async_items()[0]["type"] == "module"


async def test_older_resource_is_moved_to_the_new_version(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    other = "/local/other-card.js"
    hass_storage[RESOURCES_KEY] = _stored_resources(other, f"{CARD_URL}?v=0.0.9")
    await _setup(hass, tmp_path, aioclient_mock)
    assert await _resource_urls(hass) == [other, CURRENT]


async def test_current_resource_is_not_duplicated(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    hass_storage[RESOURCES_KEY] = _stored_resources(CURRENT)
    await _setup(hass, tmp_path, aioclient_mock)
    entry = hass.config_entries.async_entries("meteofrance_radar")[0]
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert await _resource_urls(hass) == [CURRENT]


async def test_yaml_mode_is_left_alone(
    hass: HomeAssistant,
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="custom_components.meteofrance_radar")
    await _setup(hass, tmp_path, aioclient_mock, {"resource_mode": "yaml"})
    assert CURRENT not in await _resource_urls(hass)
    assert "YAML mode" in caplog.text
    assert CARD_URL in caplog.text


async def test_static_paths_are_registered_once(
    hass: HomeAssistant,
    tmp_path: Path,
    aioclient_mock: AiohttpClientMocker,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    await _setup(hass, tmp_path, aioclient_mock)
    entry = hass.config_entries.async_entries("meteofrance_radar")[0]
    with patch.object(hass.http, "async_register_static_paths", AsyncMock()) as register:
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await async_register_frontend(hass)
    register.assert_not_called()
    client = await hass_client_no_auth()
    assert (await client.get(CARD_URL)).status == HTTPStatus.OK
    assert await _resource_urls(hass) == [CURRENT]
