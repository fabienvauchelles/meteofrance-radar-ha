"""North polar stereographic projection on the WGS84 ellipsoid, in numpy.

Météo-France publishes the 500 m mosaic in a PROJ `+proj=stere` definition. Only the
north polar case with a standard parallel is implemented here (Snyder, Map Projections:
A Working Manual, 1987, eq. 21-33 to 21-35 and 15-9), which is all the product uses and
saves shipping pyproj. Any other definition raises UnsupportedProjectionError, so a
projection change on the Météo-France side fails loudly instead of misplacing rain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import UnsupportedProjectionError

WGS84_A = 6_378_137.0
WGS84_F = 1 / 298.257223563
WGS84_E = math.sqrt(WGS84_F * (2 - WGS84_F))
NORTH_POLE_LAT = 90.0
SUPPORTED_ELLIPSOID = "WGS84"
_FLAGS = frozenset({"no_defs"})
_NUMERIC_KEYS = frozenset({"lat_0", "lat_ts", "lon_0", "x_0", "y_0"})
_TEXT_VALUES = {"proj": "stere", "ellps": "WGS84", "datum": "WGS84", "units": "m"}


@dataclass(frozen=True)
class PolarStereographic:
    """Ellipsoidal north polar stereographic with a standard parallel (WGS84).

    Attributes:
        lat_ts: Latitude of true scale, in degrees, strictly between 0 and 90.
        lon_0: Central meridian, in degrees.
        x_0: False easting, in metres.
        y_0: False northing, in metres.
    """

    lat_ts: float
    lon_0: float
    x_0: float
    y_0: float

    def forward(
        self, lon: ArrayLike, lat: ArrayLike
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Project WGS84 degrees to (x, y) metres; arrays of any matching shape."""
        phi = np.radians(np.asarray(lat, dtype=np.float64))
        lam = np.radians(np.asarray(lon, dtype=np.float64) - self.lon_0)
        phi_c = math.radians(self.lat_ts)
        sin_c = math.sin(phi_c)
        m_c = math.cos(phi_c) / math.sqrt(1 - WGS84_E**2 * sin_c**2)
        rho = WGS84_A * m_c * _t(phi) / float(_t(np.asarray(phi_c)))
        x = self.x_0 + rho * np.sin(lam)
        y = self.y_0 - rho * np.cos(lam)
        return x.astype(np.float64), y.astype(np.float64)


def _t(phi: NDArray[np.float64]) -> NDArray[np.float64]:
    """Snyder's t (eq. 15-9) for geodetic latitudes in radians."""
    e_sin = WGS84_E * np.sin(phi)
    t: NDArray[np.float64] = np.tan(np.pi / 4 - phi / 2) / ((1 - e_sin) / (1 + e_sin)) ** (
        WGS84_E / 2
    )
    return t


def _tokens(projdef: str) -> dict[str, str | None]:
    fields: dict[str, str | None] = {}
    for token in projdef.split():
        if not token.startswith("+"):
            raise UnsupportedProjectionError("projdef token without '+'", cause=token)
        key, sep, value = token[1:].partition("=")
        if key in fields:
            raise UnsupportedProjectionError("projdef repeats a parameter", cause=key)
        fields[key] = value if sep else None
    return fields


def _number(fields: dict[str, str | None], key: str, default: float | None) -> float:
    value = fields.get(key)
    if value is None:
        if default is None:
            raise UnsupportedProjectionError("projdef misses a parameter", cause=key)
        return default
    try:
        number = float(value)
    except ValueError as exc:
        raise UnsupportedProjectionError("projdef parameter is not a number", cause=key) from exc
    if not math.isfinite(number):
        raise UnsupportedProjectionError("projdef parameter is not finite", cause=key)
    return number


def _check_keys(fields: dict[str, str | None]) -> None:
    for key, value in fields.items():
        if key in _FLAGS:
            continue
        if key in _NUMERIC_KEYS:
            continue
        expected = _TEXT_VALUES.get(key)
        if expected is None:
            raise UnsupportedProjectionError("projdef parameter not supported", cause=key)
        if value != expected:
            raise UnsupportedProjectionError(
                "projdef value not supported", cause=f"{key}={value} (expected {expected})"
            )
    if "proj" not in fields:
        raise UnsupportedProjectionError("projdef misses a parameter", cause="proj")
    if "ellps" not in fields and "datum" not in fields:
        raise UnsupportedProjectionError("projdef names no ellipsoid", cause="ellps")


def parse_projdef(projdef: str) -> PolarStereographic:
    """Parse a PROJ string into a north polar stereographic on WGS84.

    Raises:
        UnsupportedProjectionError: anything but `+proj=stere +lat_0=90` with a `lat_ts`
            strictly between 0 and 90 on WGS84, or an unknown or malformed parameter.
    """
    fields = _tokens(projdef)
    _check_keys(fields)
    if _number(fields, "lat_0", None) != NORTH_POLE_LAT:
        raise UnsupportedProjectionError("only the north polar aspect is supported", cause="lat_0")
    lat_ts = _number(fields, "lat_ts", None)
    if not 0 < lat_ts < NORTH_POLE_LAT:
        raise UnsupportedProjectionError("lat_ts out of range", cause=str(lat_ts))
    return PolarStereographic(
        lat_ts=lat_ts,
        lon_0=_number(fields, "lon_0", 0.0),
        x_0=_number(fields, "x_0", 0.0),
        y_0=_number(fields, "y_0", 0.0),
    )
