"""Rain rate at the home from tiny-bbox GRIB2 requests, shared by the AROME-PI and AROME jobs.

A 0.03 degree box around the home returns a 3x3 GRIB2 of about 200 bytes. The value of
the cell holding the home is read and scaled to mm/h. Decoding runs in the executor like
every other numpy call.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from datetime import datetime
from functools import partial

from ..collector import BlockingRunner
from ..decode.grib import read_grib2
from ..decode.latlon import latlon_cell
from ..domain.forecast import (
    AROME_DOMAIN,
    MM_H_FACTOR,
    ForecastProduct,
    PinValue,
    coverage_id,
    pin_bbox,
)
from ..domain.ports import CoverageSource
from ..errors import GribFormatError

type HomeProvider = Callable[[], tuple[float, float] | None]


def home_in_domain(home: HomeProvider) -> tuple[float, float] | None:
    """The home (lon, lat) when it is set and inside the AROME domain, else None."""
    point = home()
    if point is None or not AROME_DOMAIN.contains(*point):
        return None
    return point


def pin_value_of(data: bytes, lon: float, lat: float, factor: float) -> float:
    """Rate in mm/h of the cell holding (lon, lat) in a GRIB2 message (blocking).

    Raises:
        GribFormatError: the message is unsupported, or the point is not on its grid, or
            the value is not a finite rate.
    """
    field = read_grib2(data)
    cell = latlon_cell(field.grid, lon, lat)
    if cell is None:
        raise GribFormatError("pin GRIB2 does not cover the home")
    value = float(field.values[cell]) * factor
    if not math.isfinite(value):
        raise GribFormatError("pin GRIB2 value is not finite")
    return max(value, 0.0)


async def fetch_pin_values(
    source: CoverageSource,
    product: ForecastProduct,
    run: datetime,
    valid_times: Sequence[datetime],
    home: tuple[float, float],
    run_blocking: BlockingRunner,
) -> list[PinValue]:
    """One tiny-bbox GetCoverage per valid time; values in mm/h at the home.

    Raises:
        ApiAuthError: the key is not subscribed to the product's API.
        ApiError: any other request failure.
        GribFormatError: a response cannot be decoded.
    """
    lon, lat = home
    cov = coverage_id(product, run)
    bbox = pin_bbox(lon, lat)
    factor = MM_H_FACTOR[product]
    values: list[PinValue] = []
    for valid in valid_times:
        data = await source.get_grib(cov, valid, bbox)
        mm_h = await run_blocking(partial(pin_value_of, data, lon, lat, factor))
        values.append(PinValue(valid=valid, mm_h=mm_h))
    return values
