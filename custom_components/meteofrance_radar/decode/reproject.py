"""Nearest-neighbour reprojection table from the target grid to the source grid.

One table per (source grid, target grid) pair, built in memory on first use and never
written to disk. Building one for the France grid takes about 0.1 s and 19 MB.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ..domain.grid import EARTH_RADIUS, TargetGrid
from ..domain.models import SourceGrid
from .stereo import parse_projdef

UPPER_LEFT = "UL"


@dataclass(frozen=True)
class ReprojectionTable:
    """Source cell of every target pixel, as arrays of shape (height, width).

    `idx_r` and `idx_c` are the source row (row 0 north) and column; they are 0
    wherever `valid` is False.
    """

    idx_r: NDArray[np.int32]
    idx_c: NDArray[np.int32]
    valid: NDArray[np.bool_]


def _pixel_centres_lonlat(
    target: TargetGrid,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """WGS84 degrees of every target pixel centre (inverse spherical Web Mercator)."""
    x, y = target.pixel_centers_3857()
    lon = np.degrees(x / EARTH_RADIUS)
    lat = np.degrees(2 * np.arctan(np.exp(y / EARTH_RADIUS)) - np.pi / 2)
    return lon, lat


def build_table(source: SourceGrid, target: TargetGrid) -> ReprojectionTable:
    """Map every target pixel centre to the source cell containing it.

    The corners of the file are cell edges, so the upper-left corner is the outer
    edge of cell (0, 0).

    Raises:
        UnsupportedProjectionError: the source projdef is not supported.
    """
    projection = parse_projdef(source.projdef)
    ul_lon, ul_lat = source.corner(UPPER_LEFT)
    x_ul, y_ul = projection.forward(ul_lon, ul_lat)
    lon, lat = _pixel_centres_lonlat(target)
    x, y = projection.forward(lon, lat)
    col = np.floor((x - float(x_ul)) / source.xscale)
    row = np.floor((float(y_ul) - y) / source.yscale)
    valid = np.isfinite(col) & np.isfinite(row)
    valid &= (col >= 0) & (col < source.xsize) & (row >= 0) & (row < source.ysize)
    col[~valid] = 0
    row[~valid] = 0
    return ReprojectionTable(idx_r=row.astype(np.int32), idx_c=col.astype(np.int32), valid=valid)


class TableCache:
    """Thread-safe in-memory cache of reprojection tables, one per grid pair."""

    def __init__(self) -> None:
        self._tables: dict[tuple[str, str], ReprojectionTable] = {}
        self._lock = threading.Lock()

    def get(self, source: SourceGrid, target: TargetGrid) -> ReprojectionTable:
        """Return the table for this grid pair, building it on first use.

        Raises:
            UnsupportedProjectionError: the source projdef is not supported.
        """
        key = (source.key(), target.key())
        with self._lock:
            table = self._tables.get(key)
            if table is None:
                table = build_table(source, target)
                self._tables[key] = table
            return table
