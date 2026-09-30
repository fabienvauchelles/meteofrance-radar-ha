"""Repair issues for forecast APIs the key is not subscribed to.

A 401 or 403 from a forecast API means the key lacks that subscription. The issue names
the API to subscribe to on the portal and says the key must then be regenerated and
entered through Reconfigure. It cannot be fixed from Home Assistant, so it has no fix
flow, and it disappears on the next successful fetch.
"""

from __future__ import annotations

from typing import Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, ISSUE_FORECAST_FORBIDDEN, PORTAL_URL, TRANSLATION_FORECAST_FORBIDDEN
from .domain.forecast import ForecastProduct, ForecastState, ProductStatus

PRODUCT_LABELS: Final[dict[ForecastProduct, str]] = {
    ForecastProduct.PIAF: "PIAF",
    ForecastProduct.AROMEPI: "AROME-PI",
    ForecastProduct.AROME: "AROME",
}
PORTAL_API_NAMES: Final[dict[ForecastProduct, str]] = {
    ForecastProduct.PIAF: "Modèle AROME Prévision Immédiate Agrégée Fusionnée (PIAF)",
    ForecastProduct.AROMEPI: "Modèle AROME Prévision Immédiate",
    ForecastProduct.AROME: "Modèle AROME",
}


def forecast_issue_id(product: ForecastProduct) -> str:
    """Issue id of a refused forecast API, for example ``forecast_forbidden_piaf``."""
    return ISSUE_FORECAST_FORBIDDEN.format(product=product.value)


@callback
def async_sync_forecast_issues(hass: HomeAssistant, state: ForecastState) -> None:
    """Raise the issue of every refused API; clear it once the API answers again."""
    for product in ForecastProduct:
        status = state.of(product).status
        if status is ProductStatus.FORBIDDEN:
            ir.async_create_issue(
                hass,
                DOMAIN,
                forecast_issue_id(product),
                is_fixable=False,
                is_persistent=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=TRANSLATION_FORECAST_FORBIDDEN,
                translation_placeholders={
                    "product": PRODUCT_LABELS[product],
                    "api": PORTAL_API_NAMES[product],
                },
                learn_more_url=PORTAL_URL,
            )
        elif status is ProductStatus.OK:
            ir.async_delete_issue(hass, DOMAIN, forecast_issue_id(product))


@callback
def async_delete_forecast_issues(hass: HomeAssistant) -> None:
    """Drop every forecast issue (the entry is being removed)."""
    for product in ForecastProduct:
        ir.async_delete_issue(hass, DOMAIN, forecast_issue_id(product))


def active_forecast_issues(hass: HomeAssistant) -> list[str]:
    """Ids of the forecast issues currently raised, for diagnostics."""
    registry = ir.async_get(hass)
    return [
        issue_id
        for product in ForecastProduct
        if registry.async_get_issue(DOMAIN, issue_id := forecast_issue_id(product)) is not None
    ]
