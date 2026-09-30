"""Web Mercator target grid shared by the basemap, the radar layers and the home pin."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

EARTH_RADIUS: Final = 6378137.0
TILE_SIZE: Final = 256


def mercator_xy(lon: float, lat: float) -> tuple[float, float]:
    """Project WGS84 degrees to EPSG:3857 metres."""
    x = EARTH_RADIUS * math.radians(lon)
    y = EARTH_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


@dataclass(frozen=True)
class TargetGrid:
    """EPSG:3857 raster framed by its centre and a fractional 256 px tile zoom."""

    width: int
    height: int
    center_lon: float
    center_lat: float
    zoom: float

    @property
    def resolution(self) -> float:
        """Metres per pixel."""
        return 2 * math.pi * EARTH_RADIUS / TILE_SIZE / 2**self.zoom

    @property
    def center_xy(self) -> tuple[float, float]:
        """Centre in EPSG:3857 metres."""
        return mercator_xy(self.center_lon, self.center_lat)

    @property
    def bounds_3857(self) -> tuple[float, float, float, float]:
        """(xmin, ymin, xmax, ymax) of the outer pixel edges in EPSG:3857 metres."""
        xc, yc = self.center_xy
        half_w = self.width / 2 * self.resolution
        half_h = self.height / 2 * self.resolution
        return xc - half_w, yc - half_h, xc + half_w, yc + half_h

    def lonlat_to_pixel(self, lon: float, lat: float) -> tuple[float, float]:
        """Continuous (col, row) of a WGS84 point; the pixel index is the floor."""
        x, y = mercator_xy(lon, lat)
        xc, yc = self.center_xy
        r = self.resolution
        return (x - xc) / r + self.width / 2, self.height / 2 - (y - yc) / r

    def lonlat_to_pixel_arrays(
        self, lon: NDArray[np.float64], lat: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Vectorised lonlat_to_pixel: continuous (col, row) arrays."""
        x = EARTH_RADIUS * np.radians(lon)
        y = EARTH_RADIUS * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
        xc, yc = self.center_xy
        r = self.resolution
        col = (x - xc) / r + self.width / 2
        row = self.height / 2 - (y - yc) / r
        return col.astype(np.float64), row.astype(np.float64)

    def contains_pixel(self, col: float, row: float) -> bool:
        """Return True when a continuous (col, row) falls inside the raster."""
        return 0 <= col < self.width and 0 <= row < self.height

    def pixel_centers_3857(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """EPSG:3857 (x, y) of every pixel centre, each of shape (height, width)."""
        xmin, _, _, ymax = self.bounds_3857
        r = self.resolution
        xs = xmin + (np.arange(self.width, dtype=np.float64) + 0.5) * r
        ys = ymax - (np.arange(self.height, dtype=np.float64) + 0.5) * r
        grid_x, grid_y = np.meshgrid(xs, ys)
        return grid_x, grid_y

    def as_dict(self) -> dict[str, float | int]:
        """JSON-ready grid parameters, as the frames API returns them."""
        return {
            "width": self.width,
            "height": self.height,
            "center_lon": self.center_lon,
            "center_lat": self.center_lat,
            "zoom": self.zoom,
        }

    def key(self) -> str:
        """Stable text of every field, for cache keys and style hashes."""
        return (
            f"3857:{self.width}x{self.height}"
            f"@{float(self.center_lon)!r},{float(self.center_lat)!r}z{float(self.zoom)!r}"
        )


# The grid of www/basemap.png. Layers and basemap must share it.
FRANCE_GRID: Final = TargetGrid(width=1920, height=1080, center_lon=2.5, center_lat=46.6, zoom=6.4)
