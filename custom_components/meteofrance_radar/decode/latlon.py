"""Reprojection table from the Web Mercator target grid to a regular lat/lon forecast grid.

Forecast cells are point-registered (PixelIsPoint): cell (row, col) is centred on
(lon0 + col * dlon, lat0 - row * dlat), so the nearest cell of a point is the rounded
offset. Tables are built in memory and kept in a small LRU cache, like the radar ones.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Final

import numpy as np

from ..domain.grid import EARTH_RADIUS, TargetGrid
from .grib import LatLonGrid
from .reproject import ReprojectionTable

# The PIAF grid is the only full field rendered; a second slot covers a grid change.
DEFAULT_MAX_LATLON_TABLES: Final = 2


def build_latlon_table(grid: LatLonGrid, target: TargetGrid) -> ReprojectionTable:
    """Map every target pixel centre to the nearest lat/lon cell of `grid`.

    Pixels whose nearest cell falls outside the grid are marked invalid.
    """
    x, y = target.pixel_centers_3857()
    lon = np.degrees(x / EARTH_RADIUS)
    lat = np.degrees(np.arctan(np.sinh(y / EARTH_RADIUS)))
    col = np.rint((lon - grid.lon0) / grid.dlon)
    row = np.rint((grid.lat0 - lat) / grid.dlat)
    valid = (col >= 0) & (col < grid.ni) & (row >= 0) & (row < grid.nj)
    col[~valid] = 0
    row[~valid] = 0
    return ReprojectionTable(idx_r=row.astype(np.int32), idx_c=col.astype(np.int32), valid=valid)


def latlon_cell(grid: LatLonGrid, lon: float, lat: float) -> tuple[int, int] | None:
    """(row, col) of the cell nearest to (lon, lat), or None outside the grid."""
    col = int(np.rint((lon - grid.lon0) / grid.dlon))
    row = int(np.rint((grid.lat0 - lat) / grid.dlat))
    if 0 <= col < grid.ni and 0 <= row < grid.nj:
        return row, col
    return None


class LatLonTableCache:
    """Thread-safe LRU cache of lat/lon reprojection tables (about 18 MB each for France).

    Args:
        max_tables: Most tables kept at once, at least 1.

    Raises:
        ValueError: `max_tables` is below 1.
    """

    def __init__(self, max_tables: int = DEFAULT_MAX_LATLON_TABLES) -> None:
        if max_tables < 1:
            raise ValueError(f"max_tables must be at least 1, got {max_tables}")
        self._max_tables = max_tables
        self._tables: OrderedDict[tuple[str, str], ReprojectionTable] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        """Number of tables currently held."""
        with self._lock:
            return len(self._tables)

    def get(self, grid: LatLonGrid, target: TargetGrid) -> ReprojectionTable:
        """Return the table for this grid pair, building it on first use."""
        key = (grid.key(), target.key())
        with self._lock:
            table = self._tables.get(key)
            if table is not None:
                self._tables.move_to_end(key)
                return table
            table = build_latlon_table(grid, target)
            self._tables[key] = table
            while len(self._tables) > self._max_tables:
                self._tables.popitem(last=False)
            return table
