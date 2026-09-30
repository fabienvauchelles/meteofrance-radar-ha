"""Layer rendering: the real product end to end, georeferenced peaks, and LayerService.

Rendering sits behind the layer HTTP view, whose scenarios live with the views; the
pixel-level checks below have no public-surface path, so these are focused tests.
"""

from __future__ import annotations

import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image

from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.decode.reproject import TableCache
from custom_components.meteofrance_radar.domain.grid import FRANCE_GRID, TargetGrid
from custom_components.meteofrance_radar.domain.models import AcrrFrame, Frame, FrameEntry
from custom_components.meteofrance_radar.domain.palette import (
    NODATA_INDEX,
    palette_alpha,
    palette_rgb,
)
from custom_components.meteofrance_radar.domain.rate import to_class_frame
from custom_components.meteofrance_radar.errors import SlotNotFoundError, StyleNotFoundError
from custom_components.meteofrance_radar.render.layer import render_layer
from custom_components.meteofrance_radar.render.service import LayerService
from tests.support.odim_factory import dry_raw, with_peak, write_odim

REAL_H5 = Path(__file__).parents[1] / "fixtures" / "lame_d_eau_500_20260930T1030Z.h5"
SLOT = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)
STYLE = "teststyle0"
PALETTE_ENTRIES = 12
EDGE_COLUMNS = 20
PARIS_LON, PARIS_LAT = 2.3522, 48.8566
# 1.00 mm per 5 min = 12 mm/h, class [10, 16) mm/h = palette index 7.
PEAK_RAW = 100
PEAK_INDEX = 7
# A coarse grid over the same area keeps the service tests fast.
SMALL_GRID = TargetGrid(width=96, height=54, center_lon=2.5, center_lat=46.6, zoom=2.1)


def _indices(png: bytes) -> NDArray[np.uint8]:
    with Image.open(io.BytesIO(png)) as image:
        return np.asarray(image)


@pytest.fixture(scope="module")
def real_frame() -> AcrrFrame:
    return read_product(REAL_H5.read_bytes())


def test_real_product_renders_indexed_png_with_transparency(real_frame: AcrrFrame) -> None:
    tables = TableCache()
    png = render_layer(real_frame, tables.get(real_frame.grid, FRANCE_GRID))

    with Image.open(io.BytesIO(png)) as image:
        assert image.format == "PNG"
        assert image.mode == "P"
        assert image.size == (1920, 1080)
        palette = image.getpalette()
        assert palette is not None
        assert palette[: 3 * PALETTE_ENTRIES] == palette_rgb()
        assert image.info["transparency"] == palette_alpha()
        idx = np.asarray(image)
    assert int(idx.max()) <= NODATA_INDEX
    # West and east margins lie outside the mosaic: no data, never dry.
    assert bool((idx[:, :EDGE_COLUMNS] == NODATA_INDEX).all())
    assert bool((idx[:, -EDGE_COLUMNS:] == NODATA_INDEX).all())
    assert int(np.count_nonzero(idx == 0)) > 0
    assert int(np.count_nonzero((idx >= 1) & (idx < NODATA_INDEX))) > 0


def test_downgraded_frame_renders_identically(real_frame: AcrrFrame) -> None:
    table = TableCache().get(real_frame.grid, FRANCE_GRID)

    before = _indices(render_layer(real_frame, table))
    after = _indices(render_layer(to_class_frame(real_frame), table))

    assert np.array_equal(before, after)


def test_synthetic_peak_on_paris_lands_on_paris_pixel() -> None:
    raw = with_peak(dry_raw(), PARIS_LON, PARIS_LAT, PEAK_RAW)
    frame = read_product(write_odim(slot=SLOT, raw=raw))

    idx = _indices(render_layer(frame, TableCache().get(frame.grid, FRANCE_GRID)))

    col, row = FRANCE_GRID.lonlat_to_pixel(PARIS_LON, PARIS_LAT)
    assert idx[int(row), int(col)] == PEAK_INDEX
    assert 0 < int(np.count_nonzero(idx == PEAK_INDEX)) < 30


class FakeStore:
    """In-memory FrameStore that records reads and their peak concurrency."""

    def __init__(self, frames: dict[datetime, Frame], read_delay: float = 0.0) -> None:
        self.frames = frames
        self.reads = 0
        self.peak_readers = 0
        self._readers = 0
        self._delay = read_delay
        self._lock = threading.Lock()

    def load_index(self) -> None:
        return None

    def entries(self) -> list[FrameEntry]:
        return []

    def entries_between(self, start: datetime, end: datetime) -> list[FrameEntry]:
        return []

    def exists(self, slot: datetime) -> bool:
        return slot in self.frames

    def write(self, frame: Frame) -> FrameEntry:
        raise NotImplementedError

    def read(self, slot: datetime) -> Frame:
        with self._lock:
            self.reads += 1
            self._readers += 1
            self.peak_readers = max(self.peak_readers, self._readers)
        time.sleep(self._delay)
        with self._lock:
            self._readers -= 1
        if slot not in self.frames:
            raise SlotNotFoundError("gone", slot=slot)
        return self.frames[slot]

    def delete(self, slot: datetime) -> int:
        return 0 if self.frames.pop(slot, None) is None else 1

    def total_bytes(self) -> int:
        return 0


class FakeCache:
    """In-memory LayerCache."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, datetime], bytes] = {}

    def get(self, style: str, slot: datetime) -> bytes | None:
        return self.items.get((style, slot))

    def put(self, style: str, slot: datetime, png: bytes) -> None:
        self.items[(style, slot)] = png

    def purge_other_styles(self, style: str) -> int:
        return 0

    def enforce_budget(self, budget_bytes: int) -> int:
        return 0

    def total_bytes(self) -> int:
        return 0


@pytest.fixture(scope="module")
def dry_frame() -> AcrrFrame:
    return read_product(write_odim(slot=SLOT))


def _service(store: FakeStore, cache: FakeCache) -> LayerService:
    return LayerService(store, cache, TableCache(), SMALL_GRID, STYLE)


def test_layer_service_renders_then_serves_cache_hits(dry_frame: AcrrFrame) -> None:
    store, cache = FakeStore({SLOT: dry_frame}), FakeCache()
    service = _service(store, cache)

    first = service.get_layer(STYLE, SLOT)
    second = service.get_layer(STYLE, SLOT)

    assert first == second == cache.items[(STYLE, SLOT)]
    assert _indices(first).shape == (SMALL_GRID.height, SMALL_GRID.width)
    assert store.reads == 1


def test_layer_service_cache_hit_skips_the_store() -> None:
    store, cache = FakeStore({}), FakeCache()
    cache.put(STYLE, SLOT, b"cached png")

    assert _service(store, cache).get_layer(STYLE, SLOT) == b"cached png"
    assert store.reads == 0


def test_layer_service_rejects_unknown_style_and_missing_slot(dry_frame: AcrrFrame) -> None:
    store, cache = FakeStore({SLOT: dry_frame}), FakeCache()
    service = _service(store, cache)

    with pytest.raises(StyleNotFoundError):
        service.get_layer("otherstyle", SLOT)
    with pytest.raises(SlotNotFoundError):
        service.get_layer(STYLE, SLOT + timedelta(minutes=5))
    assert store.reads == 0
    assert cache.items == {}


def test_layer_service_maps_a_frame_deleted_mid_render(dry_frame: AcrrFrame) -> None:
    class VanishingStore(FakeStore):
        def exists(self, slot: datetime) -> bool:
            return self.reads == 0

    service = _service(VanishingStore({}), FakeCache())

    with pytest.raises(SlotNotFoundError):
        service.get_layer(STYLE, SLOT)


def test_layer_service_serialises_concurrent_misses(dry_frame: AcrrFrame) -> None:
    slots = [SLOT + timedelta(minutes=5 * n) for n in range(4)]
    store = FakeStore(dict.fromkeys(slots, dry_frame), read_delay=0.05)
    cache = FakeCache()
    service = _service(store, cache)

    with ThreadPoolExecutor(max_workers=len(slots)) as pool:
        pngs = list(pool.map(lambda slot: service.get_layer(STYLE, slot), slots))

    assert len(pngs) == len(slots)
    assert store.reads == len(slots)
    assert store.peak_readers == 1
    assert len(cache.items) == len(slots)


def test_layer_service_serves_the_layer_when_caching_fails(dry_frame: AcrrFrame) -> None:
    class FullDiskCache(FakeCache):
        def put(self, style: str, slot: datetime, png: bytes) -> None:
            raise OSError(28, "No space left on device")

    service = _service(FakeStore({SLOT: dry_frame}), FullDiskCache())

    png = service.get_layer(STYLE, SLOT)

    assert _indices(png).shape == (SMALL_GRID.height, SMALL_GRID.width)
