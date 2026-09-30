"""DescribeCoverage parsing on the real documents of the three forecast APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import cast

import aiohttp
import pytest

from custom_components.meteofrance_radar.api.pacer import RequestPacer
from custom_components.meteofrance_radar.api.wcs import WcsClient, parse_describe_coverage
from custom_components.meteofrance_radar.domain.forecast import pin_bbox
from custom_components.meteofrance_radar.errors import ApiError

FORECAST_DIR = Path(__file__).parents[1] / "fixtures" / "forecast"


@pytest.mark.parametrize(
    ("name", "run", "count", "first", "last", "step"),
    [
        (
            "piaf_describe_20260930T1450Z.xml",
            datetime(2026, 9, 30, 14, 50, tzinfo=UTC),
            39,
            datetime(2026, 9, 30, 14, 55, tzinfo=UTC),
            datetime(2026, 9, 30, 18, 5, tzinfo=UTC),
            timedelta(minutes=5),
        ),
        (
            "aromepi_describe_20260930T1400Z.xml",
            datetime(2026, 9, 30, 14, 0, tzinfo=UTC),
            24,
            datetime(2026, 9, 30, 14, 15, tzinfo=UTC),
            datetime(2026, 9, 30, 20, 0, tzinfo=UTC),
            timedelta(minutes=15),
        ),
        (
            "arome_describe_20260930T1200Z.xml",
            datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
            10,
            datetime(2026, 9, 30, 13, 0, tzinfo=UTC),
            datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
            timedelta(hours=1),
        ),
    ],
)
def test_real_documents_give_their_valid_times(
    name: str, run: datetime, count: int, first: datetime, last: datetime, step: timedelta
) -> None:
    times = parse_describe_coverage((FORECAST_DIR / name).read_bytes(), run)

    assert times.run == run
    assert len(times.valid_times) == count
    assert times.valid_times[0] == first
    assert times.valid_times[-1] == last
    assert all(b - a == step for a, b in pairwise(times.valid_times))
    assert all(t.tzinfo is UTC for t in times.valid_times)


@pytest.mark.parametrize(
    "body",
    [
        (FORECAST_DIR / "wcs_404_868404.xml").read_bytes(),
        b"not xml at all",
        (FORECAST_DIR / "piaf_describe_20260930T1450Z.xml")
        .read_bytes()
        .replace(b"<gmlrgrid:gridAxesSpanned>time<", b"<gmlrgrid:gridAxesSpanned>other<"),
        (FORECAST_DIR / "piaf_describe_20260930T1450Z.xml")
        .read_bytes()
        .replace(b"2026-09-30T14:55:00Z</gml:beginPosition>", b"soon</gml:beginPosition>"),
    ],
)
def test_documents_without_a_usable_time_axis_raise(body: bytes) -> None:
    with pytest.raises(ApiError):
        parse_describe_coverage(body, datetime(2026, 9, 30, 14, 50, tzinfo=UTC))


class _Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    async def read(self) -> bytes:
        return self._body

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class _Session:
    def __init__(self, response: _Response) -> None:
        self._response = response

    def get(self, *_: object, **__: object) -> _Response:
        return self._response


async def test_pin_request_errors_never_carry_the_home_location() -> None:
    echo = (
        b"<ExceptionText>subset=long(2.445,2.475) subset=lat(48.785,48.815) "
        b"point 2.46 48.8 code 868404</ExceptionText>"
    )
    client = WcsClient(
        cast(aiohttp.ClientSession, _Session(_Response(400, echo))),
        "unused-key",
        "aromepi",
        "https://example.invalid/wcs",
        RequestPacer(max_per_minute=90, min_spacing_s=0),
    )

    with pytest.raises(ApiError) as info:
        await client.get_grib(
            "COVERAGE", datetime(2026, 9, 30, 18, tzinfo=UTC), pin_bbox(2.46, 48.80)
        )

    text = str(info.value)
    assert "aromepi GetCoverage COVERAGE HTTP 400" in text
    assert "868404" in text
    for leak in ("2.4", "48.", "unused-key"):
        assert leak not in text
