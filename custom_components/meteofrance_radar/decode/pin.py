"""Radar source cell holding a WGS84 point, with the arithmetic of the reprojection table."""

from __future__ import annotations

import math

from ..domain.models import SourceGrid
from .reproject import UPPER_LEFT
from .stereo import parse_projdef


def radar_cell(grid: SourceGrid, lon: float, lat: float) -> tuple[int, int] | None:
    """(row, col) of the source cell containing (lon, lat), or None outside the grid.

    Uses the same floor of the offset from the upper-left cell edge as
    `reproject.build_table`, so the pin reads the cell its pixel is drawn from.

    Raises:
        UnsupportedProjectionError: the grid projdef is not supported.
    """
    projection = parse_projdef(grid.projdef)
    ul_lon, ul_lat = grid.corner(UPPER_LEFT)
    x_ul, y_ul = projection.forward(ul_lon, ul_lat)
    x, y = projection.forward(lon, lat)
    col = math.floor((float(x) - float(x_ul)) / grid.xscale)
    row = math.floor((float(y_ul) - float(y)) / grid.yscale)
    if 0 <= col < grid.xsize and 0 <= row < grid.ysize:
        return row, col
    return None
