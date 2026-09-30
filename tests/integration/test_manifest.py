"""The integration is discoverable by Home Assistant with the manifest it ships."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from custom_components.meteofrance_radar.const import DOMAIN


async def test_integration_is_discoverable(hass: HomeAssistant) -> None:
    integration = await async_get_integration(hass, DOMAIN)

    assert integration.domain == DOMAIN
    assert integration.config_flow is True
    assert integration.dependencies == ["http"]
    assert integration.requirements == ["h5py==3.16.0"]
    assert str(integration.version) == "0.2.1"
