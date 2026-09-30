"""Static files for the card and the basemap, plus the card's Lovelace resource.

The card loads as a Lovelace resource rather than through ``add_extra_js_url``:
that helper injects the module during the initial page parse, before the frontend
installs its scoped custom-element registry, so the card would define itself into
a registry Home Assistant no longer reads and the tag would render as "custom
element doesn't exist". A resource is imported after that registry is in place.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import CONF_RESOURCE_TYPE_WS
from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_when_setup
from homeassistant.util.hass_dict import HassKey

from .const import BASEMAP_FILENAME, CARD_FILENAME, DOMAIN, LOGGER, URL_STATIC_BASE

WWW_DIR: Final = Path(__file__).parent / "www"
CARD_URL: Final = f"{URL_STATIC_BASE}/{CARD_FILENAME}"
BASEMAP_URL: Final = f"{URL_STATIC_BASE}/{BASEMAP_FILENAME}"
RESOURCE_TYPE_MODULE: Final = "module"

# Set once the static paths are registered: aiohttp refuses the same route twice.
_REGISTERED: HassKey[bool] = HassKey(f"{DOMAIN}_frontend_registered")


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card bundle and the basemap, then register the card resource.

    Safe to call more than once in a process: only the first call registers.
    """
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(WWW_DIR / CARD_FILENAME), True),
            StaticPathConfig(BASEMAP_URL, str(WWW_DIR / BASEMAP_FILENAME), True),
        ]
    )
    async_when_setup(hass, LOVELACE_DOMAIN, _async_register_resource)


async def _async_register_resource(hass: HomeAssistant, _component: str) -> None:
    """Add or refresh the card's Lovelace resource, versioned to bust the browser cache.

    Only storage-mode dashboards accept a resource from code. A YAML-mode instance
    keeps its resources in the file, so the URL has to be added there by hand.
    """
    resources = getattr(hass.data.get(LOVELACE_DOMAIN), "resources", None)
    if not isinstance(resources, ResourceStorageCollection):
        LOGGER.info("Lovelace is in YAML mode: add %s as a module resource by hand", CARD_URL)
        return
    integration = await async_get_integration(hass, DOMAIN)
    versioned = f"{CARD_URL}?v={integration.version}"
    # Loads the store before async_items() is read.
    await resources.async_get_info()
    for item in resources.async_items():
        if str(item.get(CONF_URL, "")).split("?", 1)[0] != CARD_URL:
            continue
        if item[CONF_URL] != versioned:
            await resources.async_update_item(item["id"], {CONF_URL: versioned})
        return
    await resources.async_create_item(
        {CONF_RESOURCE_TYPE_WS: RESOURCE_TYPE_MODULE, CONF_URL: versioned}
    )
