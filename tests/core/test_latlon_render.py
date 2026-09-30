"""Lat/lon reprojection table, pin cells and forecast layer rendering.

Pixel-level checks with no public-surface path of their own: focused tests on the real
PIAF step (valid 2026-09-30 15:20 UTC) and a synthetic field.
"""

from __future__ import annotations

import io
import lzma
import threading
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image

from custom_components.meteofrance_radar.decode.grib import GribField, LatLonGrid, read_grib2
from custom_components.meteofrance_radar.decode.latlon import (
    LatLonTableCache,
    build_latlon_table,
    latlon_cell,
)
from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.decode.pin import radar_cell
from custom_components.meteofrance_radar.decode.reproject import TableCache
from custom_components.meteofrance_radar.domain.grid import EARTH_RADIUS, FRANCE_GRID
from custom_components.meteofrance_radar.domain.palette import (
    NODATA_INDEX,
    RENDER_VERSION,
    TOP_CLASS,
    classify,
    palette_alpha,
)
from custom_components.meteofrance_radar.render.forecast import render_field_layer
from custom_components.meteofrance_radar.render.service import LayerService
from custom_components.meteofrance_radar.store.frame_store import FileFrameStore
from custom_components.meteofrance_radar.store.layer_cache import FileLayerCache
from tests.support.grib_factory import write_grib2

FIXTURES = Path(__file__).parents[1] / "fixtures"
PIAF_FULL = FIXTURES / "forecast" / "piaf_20260930T1450Z_p030.grib2.xz"
REAL_H5 = FIXTURES / "lame_d_eau_500_20260930T1030Z.h5"
PIAF_FACTOR = 12.0
PARIS_LON, PARIS_LAT = 2.3522, 48.8566
PEAK_CELL = (345, 717)
PEAK_PIXEL = (880, 411)  # (col, row)


@pytest.fixture(scope="module")
def piaf() -> GribField:
    return read_grib2(lzma.decompress(PIAF_FULL.read_bytes()))


def _indices(png: bytes) -> NDArray[np.uint8]:
    with Image.open(io.BytesIO(png)) as image:
        assert image.mode == "P"
        assert image.size == (FRANCE_GRID.width, FRANCE_GRID.height)
        assert image.info["transparency"] == palette_alpha()
        return np.asarray(image)


def test_table_covers_the_piaf_box_and_nothing_else(piaf: GribField) -> None:
    table = build_latlon_table(piaf.grid, FRANCE_GRID)

    rows, cols = np.nonzero(table.valid)
    assert abs(int(cols.min()) - 449.6) <= 1
    assert abs(int(cols.max()) + 1 - 1440.4) <= 1
    assert abs(int(rows.min()) - 90.5) <= 1
    assert abs(int(rows.max()) + 1 - 1006.5) <= 1
    assert int(table.idx_r.max()) < piaf.grid.nj
    assert int(table.idx_c.max()) < piaf.grid.ni
    assert bool((table.idx_r[~table.valid] == 0).all())


def test_latlon_cell_rounds_to_the_point_registered_cell(piaf: GribField) -> None:
    grid = piaf.grid
    assert latlon_cell(grid, -6.0, 51.5) == (0, 0)
    assert latlon_cell(grid, -6.0049, 51.5049) == (0, 0)
    assert latlon_cell(grid, -5.9949, 51.4949) == (1, 1)
    assert latlon_cell(grid, 10.5, 41.0) == (1050, 1650)
    assert latlon_cell(grid, -6.006, 51.5) is None
    assert latlon_cell(grid, 2.0, 41.0 - 0.006) is None


def test_real_piaf_step_renders_on_the_france_grid(piaf: GribField) -> None:
    table = build_latlon_table(piaf.grid, FRANCE_GRID)
    mm_h = piaf.values * np.float32(PIAF_FACTOR)

    idx = _indices(render_field_layer(mm_h, table))

    assert bool((idx[:, :449] == NODATA_INDEX).all())
    assert bool((idx[:90, :] == NODATA_INDEX).all())
    col, row = PEAK_PIXEL
    source = (int(table.idx_r[row, col]), int(table.idx_c[row, col]))
    assert abs(source[0] - PEAK_CELL[0]) <= 1
    assert abs(source[1] - PEAK_CELL[1]) <= 1
    assert int(idx[row, col]) == int(classify(mm_h[source].reshape(1))[0])
    assert int(idx[row, col]) == TOP_CLASS
    assert int(np.count_nonzero(idx == 0)) > 0


def test_synthetic_wet_cell_at_paris_renders_the_top_class() -> None:
    values = np.zeros((101, 101), dtype=np.float32)
    grid = LatLonGrid(lon0=1.85, lat0=49.35, dlon=0.01, dlat=0.01, ni=101, nj=101)
    cell = latlon_cell(grid, PARIS_LON, PARIS_LAT)
    assert cell is not None
    row0, col0 = cell
    # A 5x5 block: a 1.8 km pixel centre may sit up to a cell away from Paris.
    values[row0 - 2 : row0 + 3, col0 - 2 : col0 + 3] = 5.0
    field = read_grib2(write_grib2(values, lon0=1.85, lat0=49.35, dlon=0.01, dlat=0.01))
    table = LatLonTableCache().get(field.grid, FRANCE_GRID)

    idx = _indices(render_field_layer(field.values * np.float32(PIAF_FACTOR), table))

    col, row = FRANCE_GRID.lonlat_to_pixel(PARIS_LON, PARIS_LAT)
    assert int(idx[int(row), int(col)]) == TOP_CLASS
    assert int(idx[0, 0]) == NODATA_INDEX


def test_table_cache_reuses_and_bounds_its_tables() -> None:
    cache = LatLonTableCache(max_tables=1)
    first = LatLonGrid(lon0=0.0, lat0=50.0, dlon=0.1, dlat=0.1, ni=10, nj=10)
    second = LatLonGrid(lon0=1.0, lat0=50.0, dlon=0.1, dlat=0.1, ni=10, nj=10)

    table = cache.get(first, FRANCE_GRID)
    assert cache.get(first, FRANCE_GRID) is table
    cache.get(second, FRANCE_GRID)
    assert len(cache) == 1
    assert cache.get(first, FRANCE_GRID) is not table
    with pytest.raises(ValueError, match="max_tables"):
        LatLonTableCache(max_tables=0)


def test_radar_cell_is_the_cell_the_reprojection_table_draws() -> None:
    grid = read_product(REAL_H5.read_bytes()).grid
    table = TableCache().get(grid, FRANCE_GRID)
    x, y = FRANCE_GRID.pixel_centers_3857()
    for col, row in (PEAK_PIXEL, (960, 540), (700, 300)):
        lon = float(np.degrees(x[row, col] / EARTH_RADIUS))
        lat = float(np.degrees(np.arctan(np.sinh(y[row, col] / EARTH_RADIUS))))

        cell = radar_cell(grid, lon, lat)

        assert cell == (int(table.idx_r[row, col]), int(table.idx_c[row, col]))
    assert radar_cell(grid, -40.0, 60.0) is None


def test_layer_service_shares_the_render_lock_it_is_given(tmp_path: Path) -> None:
    lock = threading.Lock()
    store, cache = FileFrameStore(tmp_path), FileLayerCache(tmp_path)
    service = LayerService(store, cache, TableCache(), FRANCE_GRID, "s", render_lock=lock)

    assert service.render_lock is lock
    assert LayerService(store, cache, TableCache(), FRANCE_GRID, "s").render_lock is not lock
    assert RENDER_VERSION == 1
