"""WCS 2.0.1 client for the Météo-France forecast APIs (the CoverageSource port).

The key only travels in the ``apikey`` header. Pin requests carry the home bounding box
in their query string, so errors name the API, the operation, the coverage id and the
status, never the URL query nor the headers.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Final

import aiohttp

from ..const import HTTP_TIMEOUT_S
from ..domain.forecast import BBox, CoverageTimes, parse_run_id
from ..errors import ApiAuthError, ApiError
from .pacer import RequestPacer

APIKEY_HEADER: Final = "apikey"
WCS_VERSION: Final = "2.0.1"
GRIB_FORMAT: Final = "application/wmo-grib"
GRIB_MAGIC: Final = b"GRIB"
OP_DESCRIBE: Final = "DescribeCoverage"
OP_GET: Final = "GetCoverage"
ERROR_BODY_CHARS: Final = 200
TIME_AXIS: Final = "time"
_TIME_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
# A GetCoverage error body may echo the subsets, and the pin ones hold the home location.
_COORDINATES: Final = re.compile(r"-?\d+\.\d+|\b(?:long|lat)\([^)]*\)")
COORDINATE_MASK: Final = "#"
_AUTH_STATUSES: Final = frozenset({HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN})
_NS: Final = {
    "gml": "http://www.opengis.net/gml/3.2",
    "gmlrgrid": "http://www.opengis.net/gml/3.3/rgrid",
}


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime(_TIME_FORMAT)


def _parse_time(text: str | None) -> datetime:
    if text is None:
        raise ApiError("DescribeCoverage has no time axis start")
    try:
        return datetime.strptime(text.strip(), _TIME_FORMAT).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ApiError("DescribeCoverage time axis start is malformed", cause=str(exc)) from exc


def _time_coefficients(root: ET.Element) -> list[int]:
    for axis in root.iterfind(".//gmlrgrid:GeneralGridAxis", _NS):
        spanned = axis.findtext("gmlrgrid:gridAxesSpanned", default="", namespaces=_NS)
        if spanned.strip() != TIME_AXIS:
            continue
        text = axis.findtext("gmlrgrid:coefficients", default="", namespaces=_NS)
        try:
            coefficients = [int(value) for value in text.split()]
        except ValueError as exc:
            raise ApiError("DescribeCoverage time coefficients are malformed") from exc
        if coefficients:
            return coefficients
    raise ApiError("DescribeCoverage has no time axis")


def parse_describe_coverage(xml: bytes, run: datetime) -> CoverageTimes:
    """Valid times of a DescribeCoverage document.

    The time axis lists offsets in seconds from the run; `gml:beginPosition` is the
    first valid time, so the origin is that time minus the first offset.

    Args:
        xml: DescribeCoverage response body.
        run: The run the caller asked for, passed back as `CoverageTimes.run`.

    Raises:
        ApiError: the document is not XML or has no usable time axis.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ApiError("DescribeCoverage is not valid XML", cause=str(exc)) from exc
    coefficients = _time_coefficients(root)
    begin = _parse_time(root.findtext(".//gml:beginPosition", namespaces=_NS))
    origin = begin - timedelta(seconds=coefficients[0])
    valid_times = sorted({origin + timedelta(seconds=value) for value in coefficients})
    return CoverageTimes(run=run.astimezone(UTC), valid_times=tuple(valid_times))


def _run_of(coverage_id: str) -> datetime:
    """Run time embedded in a coverage id, for example "..._2026-09-30T14.50.00Z_PT5M"."""
    for part in coverage_id.split("_"):
        try:
            return parse_run_id(part)
        except ValueError:
            continue
    raise ApiError(f"coverage id holds no run time: {coverage_id}")


class WcsClient:
    """HTTP adapter over one forecast WCS endpoint.

    Args:
        session: Shared aiohttp session (Home Assistant's, in production).
        api_key: Portal API key.
        api_name: Short API name used in error messages ("piaf", "aromepi", "arome").
        base_url: WCS endpoint root, without the operation.
        pacer: Pacing shared by every request to this API.
        timeout_s: Bound on each request, in seconds.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        api_name: str,
        base_url: str,
        pacer: RequestPacer,
        timeout_s: float = HTTP_TIMEOUT_S,
    ) -> None:
        self._session = session
        self._headers = {APIKEY_HEADER: api_key}
        self._api_name = api_name
        self._base = base_url.rstrip("/")
        self._pacer = pacer
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)

    def __repr__(self) -> str:
        return f"WcsClient(api={self._api_name!r}, base={self._base!r})"

    @property
    def requests_last_minute(self) -> int:
        """Requests this API started in the last 60 seconds."""
        return self._pacer.requests_last_minute()

    async def describe(self, coverage_id: str) -> CoverageTimes | None:
        """Valid times of a run, or None when it is not published yet (404).

        Raises:
            ApiAuthError: the key was refused (401 or 403).
            ApiError: network failure, other non-2xx status or an unusable document.
        """
        params = [("service", "WCS"), ("version", WCS_VERSION), ("coverageID", coverage_id)]
        status, body = await self._get(OP_DESCRIBE, coverage_id, params)
        if status == HTTPStatus.NOT_FOUND:
            return None
        self._check(OP_DESCRIBE, coverage_id, status, body)
        return parse_describe_coverage(body, _run_of(coverage_id))

    async def get_grib(self, coverage_id: str, valid: datetime, bbox: BBox) -> bytes:
        """GRIB2 bytes of one valid time of a coverage, cut to `bbox`.

        Raises:
            ApiAuthError: the key was refused (401 or 403).
            ApiError: network failure, other non-2xx status or a body that is not GRIB.
        """
        lon_subset, lat_subset = bbox.subsets()
        params = [
            ("service", "WCS"),
            ("version", WCS_VERSION),
            ("coverageid", coverage_id),
            ("subset", f"time({_iso(valid)})"),
            ("subset", lon_subset),
            ("subset", lat_subset),
            ("format", GRIB_FORMAT),
        ]
        status, body = await self._get(OP_GET, coverage_id, params)
        self._check(OP_GET, coverage_id, status, body, scrub=True)
        if not body.startswith(GRIB_MAGIC):
            raise ApiError(
                f"{self._api_name} {OP_GET} {coverage_id} body is not GRIB",
                status=status,
                cause=_excerpt(body, scrub=True),
            )
        return body

    async def _get(
        self, op: str, coverage_id: str, params: list[tuple[str, str]]
    ) -> tuple[int, bytes]:
        await self._pacer.wait()
        try:
            async with self._session.get(
                f"{self._base}/{op}",
                params=params,
                headers=self._headers,
                timeout=self._timeout,
                allow_redirects=False,
            ) as response:
                return response.status, await response.read()
        except (aiohttp.ClientError, TimeoutError) as exc:
            # The exception text may hold the URL with its query: keep only its type.
            raise ApiError(
                f"{self._api_name} {op} {coverage_id} request failed", cause=type(exc).__name__
            ) from None

    def _check(
        self, op: str, coverage_id: str, status: int, body: bytes, *, scrub: bool = False
    ) -> None:
        message = f"{self._api_name} {op} {coverage_id} HTTP {status}"
        if status in _AUTH_STATUSES:
            raise ApiAuthError(message, status=status, cause=_excerpt(body, scrub=scrub))
        if not HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES:
            raise ApiError(message, status=status, cause=_excerpt(body, scrub=scrub))


def _excerpt(body: bytes, *, scrub: bool = False) -> str:
    """First characters of an error body; `scrub` masks decimals and echoed subsets."""
    if not scrub:
        return body[:ERROR_BODY_CHARS].decode("utf-8", "replace")
    # Mask before cutting, so a number split at the cut cannot leak its first digits.
    text = body[: ERROR_BODY_CHARS * 2].decode("utf-8", "replace")
    return _COORDINATES.sub(COORDINATE_MASK, text)[:ERROR_BODY_CHARS]
