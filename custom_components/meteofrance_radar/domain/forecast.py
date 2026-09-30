"""Forecast products, run cadence, coverage ids and the value objects the jobs exchange.

Three Météo-France WCS products feed the forecasts: PIAF (nowcast maps every 15 minutes
of a 5-minute run cadence), AROME-PI (hourly runs, 15-minute rain rate) and AROME
(3-hourly runs, hourly accumulation). PIAF values are mm per 5 minutes, the other two
are already mm/h, hence MM_H_FACTOR.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Final


class ForecastProduct(StrEnum):
    """Forecast API a value comes from."""

    PIAF = "piaf"
    AROMEPI = "aromepi"
    AROME = "arome"


class ProductStatus(StrEnum):
    """Health of one forecast product, as diagnostics and the payloads report it."""

    PENDING = "pending"
    OK = "ok"
    FORBIDDEN = "forbidden"
    ERROR = "error"
    OUTSIDE = "outside"


PIAF_LEADS_MIN: Final[tuple[int, ...]] = (*range(5, 61, 5), *range(75, 181, 15))
PIAF_RUN_STEP: Final = timedelta(minutes=15)
PIAF_LATENCY: Final = timedelta(minutes=8)
PIAF_GIVE_UP: Final = timedelta(minutes=25)
AROMEPI_RUN_STEP: Final = timedelta(hours=1)
AROMEPI_LATENCY: Final = timedelta(minutes=20)
AROMEPI_RECHECK: Final = timedelta(minutes=2)
AROMEPI_GIVE_UP: Final = timedelta(minutes=90)
AROME_RUN_STEP: Final = timedelta(hours=3)
AROME_RECHECK: Final = timedelta(hours=1)
MM_H_FACTOR: Final[Mapping[ForecastProduct, float]] = {
    ForecastProduct.PIAF: 12.0,
    ForecastProduct.AROMEPI: 1.0,
    ForecastProduct.AROME: 1.0,
}
PIN_HALF_SIZE_DEG: Final = 0.015
SAME_PIN_TOLERANCE_DEG: Final = 1e-6
_SUBSET_DECIMALS: Final = 4
_RUN_ID_FORMAT: Final = "%Y-%m-%dT%H.%M.%SZ"
_COVERAGE_PREFIX: Final[Mapping[ForecastProduct, str]] = {
    ForecastProduct.PIAF: "TOTAL_PRECIPITATION_RATE__GROUND_OR_WATER_SURFACE___",
    ForecastProduct.AROMEPI: "TOTAL_PRECIPITATION_RATE__GROUND_OR_WATER_SURFACE___",
    ForecastProduct.AROME: "TOTAL_PRECIPITATION__GROUND_OR_WATER_SURFACE___",
}
_COVERAGE_SUFFIX: Final[Mapping[ForecastProduct, str]] = {
    ForecastProduct.PIAF: "_PT5M",
    ForecastProduct.AROMEPI: "",
    ForecastProduct.AROME: "_PT1H",
}


def _subset_number(value: float) -> str:
    text = f"{value:.{_SUBSET_DECIMALS}f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


@dataclass(frozen=True)
class BBox:
    """Longitude and latitude bounds in degrees, edges included."""

    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float

    def contains(self, lon: float, lat: float) -> bool:
        """Return True when (lon, lat) lies inside the box or on its edge."""
        return self.lon_min <= lon <= self.lon_max and self.lat_min <= lat <= self.lat_max

    def subsets(self) -> tuple[str, str]:
        """WCS subset values ("long(a,b)", "lat(c,d)") with at most 4 decimals."""
        lon = f"long({_subset_number(self.lon_min)},{_subset_number(self.lon_max)})"
        lat = f"lat({_subset_number(self.lat_min)},{_subset_number(self.lat_max)})"
        return lon, lat


PIAF_BBOX: Final = BBox(-6.0, 10.5, 41.0, 51.5)
AROME_DOMAIN: Final = BBox(-12.0, 16.0, 37.5, 55.4)


def pin_bbox(lon: float, lat: float) -> BBox:
    """Tiny box around a point, wide enough for the 3x3 cells of a 0.01 degree grid."""
    return BBox(
        lon - PIN_HALF_SIZE_DEG,
        lon + PIN_HALF_SIZE_DEG,
        lat - PIN_HALF_SIZE_DEG,
        lat + PIN_HALF_SIZE_DEG,
    )


def product_domain(product: ForecastProduct) -> BBox:
    """Area a product covers: the PIAF box, or the AROME domain for AROME-PI and AROME."""
    return PIAF_BBOX if product is ForecastProduct.PIAF else AROME_DOMAIN


def _utc(t: datetime) -> datetime:
    if t.tzinfo is None:
        raise ValueError("forecast times must be timezone-aware")
    return t.astimezone(UTC)


def run_id(run: datetime) -> str:
    """Run as it appears in coverage ids, for example "2026-09-30T14.50.00Z"."""
    return _utc(run).strftime(_RUN_ID_FORMAT)


def parse_run_id(text: str) -> datetime:
    """Inverse of run_id.

    Raises:
        ValueError: `text` is not a run id.
    """
    return datetime.strptime(text, _RUN_ID_FORMAT).replace(tzinfo=UTC)


def coverage_id(product: ForecastProduct, run: datetime) -> str:
    """WCS coverage id of the precipitation field of a product run."""
    return f"{_COVERAGE_PREFIX[product]}{run_id(run)}{_COVERAGE_SUFFIX[product]}"


def floor_run(t: datetime, step: timedelta) -> datetime:
    """Latest run time at or before `t`, runs being aligned on the Unix epoch every `step`."""
    step_s = int(step.total_seconds())
    if step_s <= 0:
        raise ValueError(f"run step must be positive, got {step}")
    seconds = math.floor(_utc(t).timestamp())
    return datetime.fromtimestamp(seconds - seconds % step_s, tz=UTC)


@dataclass(frozen=True)
class CoverageTimes:
    """Valid times a published run offers, ascending."""

    run: datetime
    valid_times: tuple[datetime, ...]


@dataclass(frozen=True)
class PinValue:
    """Rain rate in mm/h at the pin for the period ending at `valid`."""

    valid: datetime
    mm_h: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.mm_h) or self.mm_h < 0:
            raise ValueError(f"pin rate must be finite and non-negative, got {self.mm_h}")


@dataclass(frozen=True)
class PinSeries:
    """Pin values of one product run, read at (lon, lat)."""

    product: ForecastProduct
    run: datetime
    lon: float
    lat: float
    values: tuple[PinValue, ...]


@dataclass(frozen=True)
class PiafStep:
    """One committed PIAF step: its valid time, lead and the pin rate (None: no pin)."""

    valid: datetime
    lead_min: int
    pin_mm_h: float | None


@dataclass(frozen=True)
class PiafRun:
    """A committed PIAF run: layers rendered in `style`, pin values read at `pin`."""

    run: datetime
    style: str
    steps: tuple[PiafStep, ...]
    pin: tuple[float, float] | None


@dataclass(frozen=True)
class ProductState:
    """Status of one product after the last tick."""

    product: ForecastProduct
    status: ProductStatus
    run: datetime | None
    last_success: datetime | None
    last_error: str | None
    next_check: datetime | None


@dataclass(frozen=True)
class ForecastState:
    """State of the three products; `products` always holds every ForecastProduct."""

    products: Mapping[ForecastProduct, ProductState]

    def of(self, product: ForecastProduct) -> ProductState:
        """State of one product."""
        return self.products[product]


def initial_state() -> ForecastState:
    """Every product PENDING, nothing fetched yet."""
    return ForecastState(
        products={
            product: ProductState(
                product=product,
                status=ProductStatus.PENDING,
                run=None,
                last_success=None,
                last_error=None,
                next_check=None,
            )
            for product in ForecastProduct
        }
    )


def same_pin(a: tuple[float, float] | None, b: tuple[float, float] | None) -> bool:
    """Return True when both points match within 1e-6 degree, or both are None."""
    if a is None or b is None:
        return a is None and b is None
    return abs(a[0] - b[0]) <= SAME_PIN_TOLERANCE_DEG and abs(a[1] - b[1]) <= SAME_PIN_TOLERANCE_DEG
