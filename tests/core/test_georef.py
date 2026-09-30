"""Georeferencing checks against references independent of the numpy projection.

Pixel positions have no public-surface path, so these are focused tests. Every expected
position is computed here with its own Web Mercator arithmetic or with pyproj (a
test-only dependency), never through the integration's reprojection code.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray
from pyproj import Transformer

from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.decode.reproject import (
    ReprojectionTable,
    TableCache,
    build_table,
)
from custom_components.meteofrance_radar.decode.stereo import parse_projdef
from custom_components.meteofrance_radar.domain.grid import TargetGrid
from custom_components.meteofrance_radar.domain.models import SourceGrid
from custom_components.meteofrance_radar.errors import UnsupportedProjectionError
from tests.support.odim_sites import read_radar_sites

WIDTH, HEIGHT = 1920, 1080
CENTER_LON, CENTER_LAT, ZOOM = 2.5, 46.6, 6.4
EARTH_RADIUS_M = 6_378_137.0
TILE_PX = 256
OPERATING_SITES = 28
PIXEL_TOLERANCE = 1
REAL_H5 = Path(__file__).parents[1] / "fixtures" / "lame_d_eau_500_20260930T1030Z.h5"


def _grid() -> TargetGrid:
    return TargetGrid(
        width=WIDTH, height=HEIGHT, center_lon=CENTER_LON, center_lat=CENTER_LAT, zoom=ZOOM
    )


def _mercator_pixel(lon: float, lat: float) -> tuple[int, int]:
    """(col, row) pixel index from Web Mercator formulas written independently of TargetGrid."""
    resolution = 2 * math.pi * EARTH_RADIUS_M / TILE_PX / 2**ZOOM

    def project(lon_deg: float, lat_deg: float) -> tuple[float, float]:
        phi = math.radians(lat_deg)
        return (
            EARTH_RADIUS_M * math.radians(lon_deg),
            EARTH_RADIUS_M * math.log(math.tan(math.pi / 4 + phi / 2)),
        )

    x, y = project(lon, lat)
    x_c, y_c = project(CENTER_LON, CENTER_LAT)
    return math.floor((x - x_c) / resolution + WIDTH / 2), math.floor(
        HEIGHT / 2 - (y - y_c) / resolution
    )


def _projected_corner(source: SourceGrid, name: str) -> tuple[float, float]:
    to_source = Transformer.from_crs("EPSG:4326", source.projdef, always_xy=True)
    x, y = to_source.transform(*source.corner(name))
    return float(x), float(y)


def _source_cell(source: SourceGrid, lon: float, lat: float) -> tuple[int, int]:
    """(row, col) of the source cell containing a point, through pyproj and the UL cell edge."""
    to_source = Transformer.from_crs("EPSG:4326", source.projdef, always_xy=True)
    x, y = to_source.transform(lon, lat)
    x_ul, y_ul = _projected_corner(source, "UL")
    return (
        math.floor((y_ul - float(y)) / source.yscale),
        math.floor((float(x) - x_ul) / source.xscale),
    )


def _pyproj_table(source: SourceGrid, target: TargetGrid) -> ReprojectionTable:
    """Reference table built with pyproj straight from EPSG:3857 pixel centres."""
    x_ul, y_ul = _projected_corner(source, "UL")
    to_source = Transformer.from_crs("EPSG:3857", source.projdef, always_xy=True)
    x, y = to_source.transform(*target.pixel_centers_3857())
    col: NDArray[np.float64] = np.floor((np.asarray(x) - x_ul) / source.xscale)
    row: NDArray[np.float64] = np.floor((y_ul - np.asarray(y)) / source.yscale)
    valid = np.isfinite(col) & np.isfinite(row)
    valid &= (col >= 0) & (col < source.xsize) & (row >= 0) & (row < source.ysize)
    col[~valid] = 0
    row[~valid] = 0
    return ReprojectionTable(idx_r=row.astype(np.int32), idx_c=col.astype(np.int32), valid=valid)


def _nearest_table_pixel(table: ReprojectionTable, row: int, col: int) -> tuple[int, int]:
    """(col, row) of the valid target pixel whose source cell is nearest to (row, col)."""
    distance = (table.idx_r.astype(np.int64) - row) ** 2 + (table.idx_c.astype(np.int64) - col) ** 2
    distance = np.where(table.valid, distance, np.iinfo(np.int64).max)
    target_row, target_col = np.unravel_index(int(np.argmin(distance)), distance.shape)
    return int(target_col), int(target_row)


@pytest.fixture(scope="module")
def real_source() -> SourceGrid:
    return read_product(REAL_H5.read_bytes()).grid


@pytest.fixture(scope="module")
def real_table(real_source: SourceGrid) -> ReprojectionTable:
    return TableCache().get(real_source, _grid())


def test_real_file_corners_are_cell_edges_and_row_zero_is_north(real_source: SourceGrid) -> None:
    x_ll, _ = _projected_corner(real_source, "LL")
    x_ur, _ = _projected_corner(real_source, "UR")
    x_ul, y_ul = _projected_corner(real_source, "UL")
    to_lonlat = Transformer.from_crs(real_source.projdef, "EPSG:4326", always_xy=True)
    centre_x = x_ul + real_source.xscale * (real_source.xsize / 2)
    _, first_row_lat = to_lonlat.transform(centre_x, y_ul - real_source.yscale * 0.5)
    _, last_row_lat = to_lonlat.transform(
        centre_x, y_ul - real_source.yscale * (real_source.ysize - 0.5)
    )

    assert (x_ur - x_ll) / real_source.xscale == pytest.approx(real_source.xsize, abs=1e-3)
    assert float(first_row_lat) > float(last_row_lat)


def test_numpy_projection_matches_pyproj(real_source: SourceGrid) -> None:
    lon, lat = np.meshgrid(np.linspace(-10, 20, 61), np.linspace(36, 56, 41))
    x_np, y_np = parse_projdef(real_source.projdef).forward(lon, lat)
    x_pp, y_pp = Transformer.from_crs("EPSG:4326", real_source.projdef, always_xy=True).transform(
        lon, lat
    )

    assert float(np.max(np.abs(x_np - x_pp))) < 1e-3
    assert float(np.max(np.abs(y_np - y_pp))) < 1e-3


def test_numpy_table_equals_pyproj_table(
    real_source: SourceGrid, real_table: ReprojectionTable
) -> None:
    reference = _pyproj_table(real_source, _grid())

    assert np.array_equal(real_table.valid, reference.valid)
    assert np.array_equal(real_table.idx_r, reference.idx_r)
    assert np.array_equal(real_table.idx_c, reference.idx_c)
    assert real_table.idx_r.shape == (HEIGHT, WIDTH)
    assert 0.3 < float(real_table.valid.mean()) < 1.0


def test_operating_radar_sites_land_on_their_web_mercator_pixel(
    real_source: SourceGrid, real_table: ReprojectionTable
) -> None:
    sites = [site for site in read_radar_sites(REAL_H5) if site.operating]
    assert len(sites) == OPERATING_SITES

    for site in sites:
        cell_row, cell_col = _source_cell(real_source, site.lon, site.lat)
        expected_col, expected_row = _mercator_pixel(site.lon, site.lat)
        col, row = _nearest_table_pixel(real_table, cell_row, cell_col)

        assert abs(col - expected_col) <= PIXEL_TOLERANCE, site.name
        assert abs(row - expected_row) <= PIXEL_TOLERANCE, site.name
        assert bool(real_table.valid[expected_row, expected_col]), site.name


def test_table_cache_builds_each_grid_pair_once(real_source: SourceGrid) -> None:
    cache = TableCache()

    first = cache.get(real_source, _grid())

    assert cache.get(real_source, _grid()) is first


@pytest.mark.parametrize(
    "projdef",
    [
        "+proj=lcc +lat_1=45 +lat_2=50 +lat_0=46 +lon_0=3 +ellps=WGS84",
        "+proj=stere +lat_0=-90 +lat_ts=-45 +ellps=WGS84",
        "+proj=stere +lat_0=90 +lat_ts=45 +ellps=GRS80",
        "+proj=stere +lat_0=90 +lat_ts=45 +ellps=WGS84 +k_0=0.99",
        "+proj=stere +lat_0=90 +ellps=WGS84",
        "+proj=stere +lat_0=90 +lat_ts=90 +ellps=WGS84",
        "+proj=stere +lat_0=90 +lat_ts=45",
        "+proj=stere +lat_0=90 +lat_ts=abc +ellps=WGS84",
        "EPSG:3995",
        "",
    ],
    ids=[
        "lcc",
        "south-pole",
        "other-ellipsoid",
        "scale-factor",
        "no-lat-ts",
        "lat-ts-pole",
        "no-ellipsoid",
        "not-a-number",
        "epsg-code",
        "empty",
    ],
)
def test_unsupported_projdef_raises(projdef: str) -> None:
    with pytest.raises(UnsupportedProjectionError):
        parse_projdef(projdef)


def test_unsupported_projdef_raises_when_building_a_table(real_source: SourceGrid) -> None:
    source = SourceGrid(
        projdef="+proj=merc +ellps=WGS84",
        xsize=real_source.xsize,
        ysize=real_source.ysize,
        xscale=real_source.xscale,
        yscale=real_source.yscale,
        corners=real_source.corners,
    )

    with pytest.raises(UnsupportedProjectionError):
        build_table(source, _grid())
