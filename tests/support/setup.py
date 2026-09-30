"""Set the integration up the way a user would end up with it: one entry, storage on tmp_path."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.meteofrance_radar.const import (
    CONF_API_KEY,
    CONF_SIZE_CAP_MB,
    CONF_STORAGE_PATH,
    DEFAULT_SIZE_CAP_MB,
    DOMAIN,
    POLL_INTERVAL,
)
from tests.support.mf_api import VALID_KEY

TITLE = "Météo-France Radar"
NOW = "2026-09-30T10:33:00+00:00"


def use_tmp_media(hass: HomeAssistant, tmp_path: Path) -> Path:
    """Point the local media folder at ``tmp_path``; return the default storage root.

    The harness puts it inside its own config folder, which must never be written to.
    """
    media = tmp_path / "media"
    hass.config.media_dirs = {"local": str(media)}
    return media / "meteofrance_radar"


def frame_files(root: Path) -> list[Path]:
    """Every stored frame file under a storage root, sorted."""
    return sorted((root / "frames").rglob("*.mfr"))


def files_with_suffix(root: Path, suffix: str) -> list[Path]:
    """Every file under ``root`` with the given suffix."""
    return sorted(path for path in root.rglob(f"*{suffix}") if path.is_file())


async def async_tick(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    delta: timedelta = POLL_INTERVAL + timedelta(seconds=1),
) -> None:
    """Move the clock forward and let the due collector pass run to completion."""
    freezer.tick(delta)
    async_fire_time_changed(hass)
    # Scheduled refreshes run as background tasks, which a plain block_till_done skips.
    await hass.async_block_till_done(wait_background_tasks=True)


def radar_entry(
    storage: Path, *, key: str = VALID_KEY, options: dict[str, Any] | None = None
) -> MockConfigEntry:
    """A config entry whose frames live under ``storage``."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        data={CONF_API_KEY: key},
        options={
            CONF_STORAGE_PATH: str(storage),
            CONF_SIZE_CAP_MB: DEFAULT_SIZE_CAP_MB,
            **(options or {}),
        },
    )


async def async_setup_integration(
    hass: HomeAssistant,
    storage: Path,
    *,
    key: str = VALID_KEY,
    options: dict[str, Any] | None = None,
    expect: ConfigEntryState = ConfigEntryState.LOADED,
) -> MockConfigEntry:
    """Add the entry, set it up and wait until the first pass is done.

    The API must be mocked beforehand (``tests.support.mf_api.mock_api``).
    """
    entry = radar_entry(storage, key=key, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is expect
    return entry
