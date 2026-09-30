"""Météo-France DPRadar API doubles for ``aioclient_mock``, and API keys shaped like the real ones.

The catalogue body is the real response saved in the fixtures, with the validity time
of its 500 m link replaced. Keys are unsigned JWTs: the integration only reads ``exp``.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from functools import cache
from http import HTTPStatus
from typing import Any

from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meteofrance_radar.const import API_BASE_URL
from tests.conftest import CATALOGUE_FIXTURE
from tests.support.odim_factory import write_odim

CATALOGUE_URL = f"{API_BASE_URL}/mosaiques/METROPOLE/observations/LAME_D_EAU"
PRODUCT_URL = f"{CATALOGUE_URL}/produit?maille=500"
FIXTURE_SLOT = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)
KEY_EXPIRY = datetime(2027, 9, 30, tzinfo=UTC)
SUSPENDED_BODY = {"code": "303001", "message": "endpoint SUSPENDED"}
VALIDITY_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _b64(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_key(expiry: datetime, subject: str = "radar-tests") -> str:
    """An unsigned JWT whose ``exp`` claim is ``expiry``."""
    header = _b64({"alg": "none", "typ": "JWT"})
    claims = _b64({"sub": subject, "exp": int(expiry.timestamp())})
    return f"{header}.{claims}.c2lnbmF0dXJl"


VALID_KEY = make_key(KEY_EXPIRY)


@cache
def dry_product(slot: datetime) -> bytes:
    """A synthetic, dry 500 m product for ``slot`` (cheaper to store than the real one)."""
    return write_odim(slot=slot)


def catalogue_body(validity: datetime) -> dict[str, Any]:
    """The real catalogue with every product link set to ``validity``."""
    body: dict[str, Any] = json.loads(CATALOGUE_FIXTURE.read_text(encoding="utf-8"))
    stamp = validity.astimezone(UTC).strftime(VALIDITY_FORMAT)
    for link in body["links"]:
        if "validity_time" in link:
            link["validity_time"] = stamp
    return body


def mock_api(
    aioclient_mock: AiohttpClientMocker, validity: datetime, product: bytes | None = None
) -> None:
    """Replace every registered response with a catalogue at ``validity`` and a product."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(CATALOGUE_URL, json=catalogue_body(validity))
    if product is not None:
        aioclient_mock.get(PRODUCT_URL, content=product)


def mock_catalogue_error(
    aioclient_mock: AiohttpClientMocker,
    status: HTTPStatus,
    body: dict[str, Any] | None = None,
) -> None:
    """Replace every registered response with a failing catalogue."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(CATALOGUE_URL, status=status, json=body or {})


def mock_catalogue_unreachable(aioclient_mock: AiohttpClientMocker) -> None:
    """Replace every registered response with a catalogue that times out."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(CATALOGUE_URL, exc=TimeoutError())


def calls_to(aioclient_mock: AiohttpClientMocker, url: str) -> int:
    """Number of requests made to ``url`` since the last ``clear_requests``."""
    return sum(
        1 for _method, called, _data, _headers in aioclient_mock.mock_calls if str(called) == url
    )


def api_key_headers(aioclient_mock: AiohttpClientMocker) -> list[str | None]:
    """The ``apikey`` header of every recorded request."""
    return [
        (headers or {}).get("apikey") for _method, _url, _data, headers in aioclient_mock.mock_calls
    ]
