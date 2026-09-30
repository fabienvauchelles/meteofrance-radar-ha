"""Shared fixtures for every test.

Home Assistant only loads integrations from custom_components when the harness is
told to, so that switch is on for the whole suite. The fixture paths point at real
Météo-France data: the georeferencing tests depend on the HDF5 product, so it is
never replaced by a synthetic one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PRODUCT_FIXTURE = FIXTURES_DIR / "lame_d_eau_500_20260930T1030Z.h5"
CATALOGUE_FIXTURE = FIXTURES_DIR / "catalogue_lame_d_eau.json"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration from custom_components."""


@pytest.fixture
def product_bytes() -> bytes:
    """The real 500 m lame d'eau product, as the API returns it."""
    return PRODUCT_FIXTURE.read_bytes()


@pytest.fixture
def catalogue_json() -> str:
    """The real catalogue response for the lame d'eau product."""
    return CATALOGUE_FIXTURE.read_text(encoding="utf-8")
