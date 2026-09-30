"""DPRadar client for the latest 500 m lame d'eau product (the ProductSource port).

URLs are always built from the base URL: the catalogue ``href``s omit ``/v1`` and are
never followed. The key only ever travels in the ``apikey`` header (``Authorization:
Bearer`` gets a 401). Errors carry the URL and status, never the headers, so the key
cannot leak through an exception message or a log line.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import aiohttp

from ..const import API_BASE_URL, HTTP_TIMEOUT_S
from ..errors import ApiAuthError, ApiError

CATALOGUE_PATH = "/mosaiques/METROPOLE/observations/LAME_D_EAU"
PRODUCT_QUERY = "produit?maille=500"
PRODUCT_PATH = f"{CATALOGUE_PATH}/{PRODUCT_QUERY}"
APIKEY_HEADER = "apikey"
VALIDITY_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ERROR_BODY_CHARS = 200
AUTH_STATUSES = frozenset({HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN})


class DPRadarClient:
    """HTTP adapter over the Météo-France DPRadar API.

    Args:
        session: Shared aiohttp session (Home Assistant's, in production).
        api_key: Portal API key.
        base_url: API root, ``/v1`` included.
        timeout_s: Bound on each request, in seconds.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        base_url: str = API_BASE_URL,
        timeout_s: float = HTTP_TIMEOUT_S,
    ) -> None:
        base = base_url.rstrip("/")
        self.catalogue_url = f"{base}{CATALOGUE_PATH}"
        self.product_url = f"{base}{PRODUCT_PATH}"
        self._session = session
        self._headers = {APIKEY_HEADER: api_key}
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)

    def __repr__(self) -> str:
        return f"DPRadarClient(base={self.catalogue_url!r})"

    async def latest_validity_time(self) -> datetime:
        """Validity time of the catalogue's 500 m link, as an aware UTC datetime.

        Raises:
            ApiAuthError: the key was refused (401 or 403).
            ApiError: network failure, other non-2xx status, bad JSON or no usable link.
        """
        body = await self._get(self.catalogue_url)
        try:
            document: Any = json.loads(body)
        except ValueError as exc:
            raise ApiError("catalogue is not valid JSON", cause=str(exc)) from exc
        return _validity_of_500m_link(document)

    async def download_latest(self) -> bytes:
        """Download the latest 500 m product file (ODIM HDF5, about 2 MB).

        Raises:
            ApiAuthError: the key was refused (401 or 403).
            ApiError: network failure or other non-2xx status.
        """
        return await self._get(self.product_url)

    async def _get(self, url: str) -> bytes:
        try:
            async with self._session.get(
                url, headers=self._headers, timeout=self._timeout, allow_redirects=False
            ) as response:
                body = await response.read()
                status = response.status
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ApiError(
                f"request failed url={url}", cause=f"{type(exc).__name__}: {exc}"
            ) from exc
        if status in AUTH_STATUSES:
            raise ApiAuthError(f"HTTP {status} url={url}", status=status)
        if not HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES:
            raise ApiError(
                f"HTTP {status} url={url}",
                status=status,
                cause=body[:ERROR_BODY_CHARS].decode("utf-8", "replace"),
            )
        return body


def _validity_of_500m_link(document: Any) -> datetime:
    links = document.get("links") if isinstance(document, dict) else None
    if not isinstance(links, list):
        raise ApiError("catalogue has no links")
    for link in links:
        if isinstance(link, dict) and str(link.get("href", "")).endswith(PRODUCT_QUERY):
            return _parse_validity(link.get("validity_time"))
    raise ApiError(f"catalogue has no {PRODUCT_QUERY} link")


def _parse_validity(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ApiError("catalogue 500 m link has no validity_time")
    try:
        return datetime.strptime(value, VALIDITY_FORMAT).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ApiError(f"catalogue validity_time is malformed: {value!r}", cause=str(exc)) from exc
