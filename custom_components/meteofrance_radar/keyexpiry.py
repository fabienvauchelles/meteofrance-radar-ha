"""API key expiry: a repair issue ahead of time, reauth once the key has expired.

Météo-France keys are JWTs whose ``exp`` claim is set when they are generated on the
portal, typically a year ahead. The claim is read without verifying the signature; a
key that is not a JWT has no known expiry and is left alone.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir

from .api.apikey import api_key_expiry
from .const import CONF_API_KEY, DOMAIN, ISSUE_KEY_EXPIRING, KEY_EXPIRY_WARNING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

PORTAL_URL = "https://portail-api.meteofrance.fr/"
EXPIRY_DATE_FORMAT = "%Y-%m-%d"


@callback
def async_check_key_expiry(hass: HomeAssistant, entry: ConfigEntry, now: datetime) -> None:
    """Raise or clear the expiring-key issue for the entry's key.

    A key with no readable ``exp`` claim has no known expiry and never raises the issue.

    Raises:
        ConfigEntryAuthFailed: the key has already expired.
    """
    expiry = api_key_expiry(entry.data[CONF_API_KEY])
    if expiry is None:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_KEY_EXPIRING)
        return
    if expiry <= now:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_KEY_EXPIRING)
        raise ConfigEntryAuthFailed("the Météo-France API key has expired")
    if expiry - now <= KEY_EXPIRY_WARNING:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_KEY_EXPIRING,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_KEY_EXPIRING,
            translation_placeholders={"expiry": expiry.strftime(EXPIRY_DATE_FORMAT)},
            learn_more_url=PORTAL_URL,
            data={"entry_id": entry.entry_id},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_KEY_EXPIRING)


def key_is_expired(key: str, now: datetime) -> bool:
    """True when the key's ``exp`` claim is in the past."""
    expiry = api_key_expiry(key)
    return expiry is not None and expiry <= now
