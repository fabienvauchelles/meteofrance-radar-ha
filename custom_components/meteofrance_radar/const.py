"""Constants shared by the integration: identifiers, config keys, defaults and limits."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

DOMAIN: Final = "meteofrance_radar"
LOGGER: Final = logging.getLogger(__package__)

CONF_API_KEY: Final = "api_key"
CONF_STORAGE_PATH: Final = "storage_path"
CONF_SIZE_CAP_MB: Final = "size_cap_mb"

DEFAULT_SIZE_CAP_MB: Final = 500
MIN_SIZE_CAP_MB: Final = 100
MAX_SIZE_CAP_MB: Final = 100_000
BYTES_PER_MB: Final = 1_000_000
STORAGE_SUBDIR: Final = "meteofrance_radar"

API_BASE_URL: Final = "https://public-api.meteofrance.fr/public/DPRadar/v1"
POLL_INTERVAL: Final = timedelta(seconds=60)
HTTP_TIMEOUT_S: Final = 30
KEY_EXPIRY_WARNING: Final = timedelta(days=14)

MIN_FREE_BYTES: Final = 1_000_000_000
LAYER_CACHE_SHARE: Final = 0.10

URL_FRAMES: Final = "/api/meteofrance_radar/frames"
URL_LAYERS: Final = "/api/meteofrance_radar/layers/{style}/{name}"
URL_STATIC_BASE: Final = "/meteofrance_radar"
CARD_FILENAME: Final = "meteofrance-radar-card.js"
BASEMAP_FILENAME: Final = "basemap.png"

ISSUE_KEY_EXPIRING: Final = "api_key_expiring"
ISSUE_FORECAST_FORBIDDEN: Final = "forecast_forbidden_{product}"
TRANSLATION_FORECAST_FORBIDDEN: Final = "forecast_forbidden"
PORTAL_URL: Final = "https://portail-api.meteofrance.fr/"

PIAF_WCS_URL: Final = (
    "https://api.meteofrance.fr/pro/piaf/1.0/wcs/MF-NWP-HIGHRES-PIAF-001-FRANCE-WCS"
)
AROMEPI_WCS_URL: Final = (
    "https://public-api.meteofrance.fr/public/aromepi/1.0/wcs/MF-NWP-HIGHRES-AROMEPI-001-FRANCE-WCS"
)
AROME_WCS_URL: Final = (
    "https://public-api.meteofrance.fr/public/arome/1.0/wcs/MF-NWP-HIGHRES-AROME-001-FRANCE-WCS"
)
FORECAST_POLL_INTERVAL: Final = timedelta(seconds=60)
FORECAST_MAX_PER_MINUTE: Final = 90
FORECAST_MIN_SPACING_S: Final = 0.7
FORECAST_SUBDIR: Final = "forecast"
URL_FORECAST_LAYERS: Final = "/api/meteofrance_radar/forecast/{style}/{run}/{name}"
URL_PIN_SERIES: Final = "/api/meteofrance_radar/pin_series"

ATTRIBUTION_RADAR: Final = "Météo-France"
ATTRIBUTION_BASEMAP: Final = "IGN ADMIN EXPRESS 2018 (via france-geojson), Natural Earth"
