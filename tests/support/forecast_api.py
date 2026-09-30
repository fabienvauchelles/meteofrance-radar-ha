"""A fake of the three Météo-France forecast WCS APIs for ``aioclient_mock``.

Each API answers from what the test published on it: DescribeCoverage returns the real
fixture document with the run and its valid times rewritten, GetCoverage returns GRIB2
bytes for a published valid time, and anything else gets the real 404 body. A status
can be forced on a whole API (403 for a missing subscription, 500 for an outage).

``aioclient_mock.clear_requests()`` drops every route, so the ``mf_api`` helpers call
``mock_forecast_absent`` after it. The routes point at one fake per mocker, so what a
test published survives the radar helpers resetting their own routes.
"""

from __future__ import annotations

import lzma
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import cache
from http import HTTPStatus
from typing import Any, Final
from urllib.parse import parse_qs
from weakref import WeakKeyDictionary

import numpy as np
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from yarl import URL

from custom_components.meteofrance_radar.const import (
    AROME_WCS_URL,
    AROMEPI_WCS_URL,
    PIAF_WCS_URL,
)
from custom_components.meteofrance_radar.domain.forecast import (
    ForecastProduct,
    coverage_id,
    parse_run_id,
    run_id,
)
from tests.conftest import FIXTURES_DIR
from tests.support.grib_factory import write_grib2

FORECAST_FIXTURES: Final = FIXTURES_DIR / "forecast"
BASE_URLS: Final = {
    ForecastProduct.PIAF: PIAF_WCS_URL,
    ForecastProduct.AROMEPI: AROMEPI_WCS_URL,
    ForecastProduct.AROME: AROME_WCS_URL,
}
DESCRIBE_TEMPLATES: Final = {
    ForecastProduct.PIAF: "piaf_describe_20260930T1450Z.xml",
    ForecastProduct.AROMEPI: "aromepi_describe_20260930T1400Z.xml",
    ForecastProduct.AROME: "arome_describe_20260930T1200Z.xml",
}
PIAF_OFFSETS_S: Final = tuple(range(300, 11_701, 300))
AROMEPI_OFFSETS_S: Final = tuple(range(900, 21_601, 900))
FORBIDDEN_BODY: Final = b'{"code":"900908","message":"Resource forbidden"}'
OUTAGE_BODY: Final = b'{"code":"303001","message":"endpoint SUSPENDED"}'
AROMEPI_PIN_MM_H: Final = 0.4296875
AROME_PIN_MM_H: Final = 0.17578125
_TIME_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"
_RUN_IN_ID: Final = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}\.\d{2}\.\d{2}Z")
_TIME_SUBSET: Final = re.compile(r"^time\((.+)\)$")
_ROUTES: Final = [re.compile(f"^{re.escape(base)}/") for base in BASE_URLS.values()]

type GribSource = Callable[[datetime, datetime], bytes]


@cache
def piaf_grib() -> bytes:
    """The real PIAF 14:50 +30 min step on the full France box (3.5 MB)."""
    return lzma.decompress((FORECAST_FIXTURES / "piaf_20260930T1450Z_p030.grib2.xz").read_bytes())


@cache
def dry_piaf_grib() -> bytes:
    """A dry field on the PIAF box at 0.1 degree: renders four times faster than the real one."""
    return write_grib2(np.zeros((106, 166)), lon0=-6.0, lat0=51.5, dlon=0.1, dlat=0.1)


@cache
def fixture_bytes(name: str) -> bytes:
    """A forecast fixture file."""
    return (FORECAST_FIXTURES / name).read_bytes()


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime(_TIME_FORMAT)


def describe_document(product: ForecastProduct, run: datetime, offsets_s: tuple[int, ...]) -> bytes:
    """The fixture DescribeCoverage of `product`, rewritten for `run` and its offsets."""
    text = fixture_bytes(DESCRIBE_TEMPLATES[product]).decode("utf-8")
    text = _RUN_IN_ID.sub(run_id(run), text)
    first, last = run + timedelta(seconds=offsets_s[0]), run + timedelta(seconds=offsets_s[-1])
    text = re.sub(r"(<gml:beginPosition[^>]*>)[^<]*", rf"\g<1>{_iso(first)}", text)
    text = re.sub(r"(<gml:endPosition[^>]*>)[^<]*", rf"\g<1>{_iso(last)}", text)
    coefficients = " ".join(str(offset) for offset in offsets_s)
    text = re.sub(
        r"<gmlrgrid:coefficients>[^<]*</gmlrgrid:coefficients>",
        f"<gmlrgrid:coefficients>{coefficients}</gmlrgrid:coefficients>",
        text,
    )
    return text.encode("utf-8")


def _default_grib(product: ForecastProduct) -> GribSource:
    if product is ForecastProduct.PIAF:
        return lambda _run, _valid: piaf_grib()
    name = (
        "aromepi_pin_20260930T1400Z_1800Z.grib2"
        if product is ForecastProduct.AROMEPI
        else "arome_pin_20260930T1200Z_2100Z.grib2"
    )
    return lambda _run, _valid: fixture_bytes(name)


@dataclass
class WcsFake:
    """One forecast API: its published runs, a forced status and its GRIB2 bytes."""

    product: ForecastProduct
    runs: dict[datetime, tuple[int, ...]] = field(default_factory=dict)
    status: HTTPStatus | None = None
    grib: GribSource | None = None

    def publish(self, run: datetime, offsets_s: tuple[int, ...] | None = None) -> None:
        """Make `run` available with valid times at `run + offsets` (seconds)."""
        if offsets_s is None:
            offsets_s = (
                PIAF_OFFSETS_S if self.product is ForecastProduct.PIAF else AROMEPI_OFFSETS_S
            )
        self.runs[run] = offsets_s

    def respond(self, url: URL) -> tuple[HTTPStatus, bytes]:
        """Status and body for a request to this API."""
        if self.status is not None:
            forbidden = self.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)
            return self.status, FORBIDDEN_BODY if forbidden else OUTAGE_BODY
        query = parse_qs(url.query_string)
        operation = url.path.rsplit("/", 1)[-1]
        ids = query.get("coverageID") or query.get("coverageid") or [""]
        match = _RUN_IN_ID.search(ids[0])
        run = parse_run_id(match.group(0)) if match else None
        offsets = self.runs.get(run) if run is not None else None
        if run is None or offsets is None or ids[0] != coverage_id(self.product, run):
            return HTTPStatus.NOT_FOUND, fixture_bytes("wcs_404_868404.xml")
        if operation == "DescribeCoverage":
            return HTTPStatus.OK, describe_document(self.product, run, offsets)
        valid = valid_time_of(url)
        if valid is None or int((valid - run).total_seconds()) not in offsets:
            return HTTPStatus.NOT_FOUND, fixture_bytes("wcs_404_868404.xml")
        source = self.grib or _default_grib(self.product)
        return HTTPStatus.OK, source(run, valid)


class ForecastApi:
    """The three forecast APIs of one test; nothing is published at first."""

    def __init__(self) -> None:
        self.apis = {product: WcsFake(product) for product in ForecastProduct}

    def __getitem__(self, product: ForecastProduct) -> WcsFake:
        return self.apis[product]

    async def respond(self, method: str, url: URL, data: Any) -> AiohttpClientMockResponse:
        """``aioclient_mock`` side effect routing a request to its API."""
        for product, base in BASE_URLS.items():
            if str(url).startswith(f"{base}/"):
                status, body = self.apis[product].respond(url)
                return AiohttpClientMockResponse(method, url, status=status, response=body)
        raise AssertionError(f"not a forecast API: {url.host}")


_FAKES: WeakKeyDictionary[AiohttpClientMocker, ForecastApi] = WeakKeyDictionary()


def forecast_api(aioclient_mock: AiohttpClientMocker) -> ForecastApi:
    """The forecast fake behind `aioclient_mock`, created on first use."""
    fake = _FAKES.get(aioclient_mock)
    if fake is None:
        fake = _FAKES[aioclient_mock] = ForecastApi()
    return fake


def mock_forecast_absent(aioclient_mock: AiohttpClientMocker) -> None:
    """Route the three forecast APIs to the fake; with nothing published, every call is 404."""
    fake = forecast_api(aioclient_mock)
    for route in _ROUTES:
        aioclient_mock.get(route, side_effect=fake.respond)


def mock_forecast_forbidden(aioclient_mock: AiohttpClientMocker, product: ForecastProduct) -> None:
    """Make one forecast API refuse the key (403), as without its subscription."""
    forecast_api(aioclient_mock)[product].status = HTTPStatus.FORBIDDEN


def valid_time_of(url: URL) -> datetime | None:
    """The ``subset=time(...)`` value of a GetCoverage URL."""
    for subset in parse_qs(url.query_string).get("subset", []):
        if match := _TIME_SUBSET.match(subset):
            return datetime.strptime(match.group(1), _TIME_FORMAT).replace(tzinfo=UTC)
    return None


def wcs_calls(
    aioclient_mock: AiohttpClientMocker, product: ForecastProduct, operation: str | None = None
) -> list[tuple[URL, dict[str, str]]]:
    """(URL, headers) of every request made to a forecast API, optionally one operation."""
    base = BASE_URLS[product]
    calls = []
    for _method, url, _data, headers in aioclient_mock.mock_calls:
        called = URL(str(url))
        if not str(called).startswith(f"{base}/"):
            continue
        if operation is None or called.path.endswith(f"/{operation}"):
            calls.append((called, dict(headers or {})))
    return calls


def forecast_call_count(aioclient_mock: AiohttpClientMocker) -> int:
    """Requests made to any forecast API."""
    return sum(len(wcs_calls(aioclient_mock, product)) for product in ForecastProduct)
