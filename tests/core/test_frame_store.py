"""FileFrameStore, FileLayerCache and Maintenance on a real directory tree under tmp_path."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from custom_components.meteofrance_radar.domain.models import (
    AcrrFrame,
    ClassFrame,
    FrameKind,
    Scaling,
    SourceGrid,
)
from custom_components.meteofrance_radar.domain.rate import to_class_frame
from custom_components.meteofrance_radar.domain.tiers import Tier, tier_of
from custom_components.meteofrance_radar.errors import SlotNotFoundError, StyleNotFoundError
from custom_components.meteofrance_radar.store.frame_store import FileFrameStore
from custom_components.meteofrance_radar.store.layer_cache import FileLayerCache
from custom_components.meteofrance_radar.store.maintenance import (
    MAX_DOWNGRADES_PER_RUN,
    Maintenance,
)

NOW = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)
STYLE = "3fa1c09b2e"
FIVE_MIN = timedelta(minutes=5)
BIG_CAP = 10**9
GRID = SourceGrid(
    projdef="+proj=stere +lat_0=90 +lon_0=0 +lat_ts=45 +ellps=WGS84",
    xsize=8,
    ysize=8,
    xscale=500.0,
    yscale=500.0,
    corners=(("UL", -9.9, 53.6), ("UR", 16.5, 53.3), ("LR", 11.8, 39.9), ("LL", -5.6, 40.1)),
)
SCALING = Scaling(gain=0.01, offset=0.0, nodata=65535.0, undetect=65534.0)


@dataclass
class FixedClock:
    at: datetime

    def now(self) -> datetime:
        return self.at


def make_frame(slot: datetime) -> AcrrFrame:
    """Small frame whose values depend on the slot, with a nodata and an undetect cell."""
    raw = ((np.arange(64, dtype=np.uint32) * 37 + slot.hour * 60 + slot.minute) % 3000).astype(
        np.uint16
    )
    raw[0] = 65535
    raw[1] = 65534
    return AcrrFrame(slot=slot, grid=GRID, scaling=SCALING, raw=raw.reshape(8, 8))


def slots_every(start: datetime, end: datetime, step: timedelta) -> list[datetime]:
    out, t = [], start
    while t < end:
        out.append(t)
        t += step
    return out


def test_write_read_exists_delete_and_reload(tmp_path: Path) -> None:
    store = FileFrameStore(tmp_path)
    store.load_index()
    slots = slots_every(NOW - timedelta(hours=1), NOW, FIVE_MIN)
    written = [store.write(make_frame(slot)) for slot in slots]

    assert [e.slot for e in store.entries()] == slots
    assert all(e.kind is FrameKind.ACRR_U16 for e in written)
    assert store.path_for(slots[0]) == tmp_path / "frames/2026/09/30/20260930T0930Z.mfr"
    assert store.total_bytes() == sum(p.stat().st_size for p in tmp_path.rglob("*.mfr"))
    between = store.entries_between(slots[2], slots[5])
    assert [e.slot for e in between] == slots[2:5]
    assert store.entries_between(NOW, NOW + timedelta(hours=1)) == []

    read = store.read(slots[3])
    assert isinstance(read, AcrrFrame)
    assert np.array_equal(read.raw, make_frame(slots[3]).raw)

    replaced = store.write(to_class_frame(make_frame(slots[3])))
    assert replaced.kind is FrameKind.CLASS_U8
    assert isinstance(store.read(slots[3]), ClassFrame)
    assert len(store.entries()) == len(slots)

    size = store.path_for(slots[4]).stat().st_size
    assert store.delete(slots[4]) == size
    assert store.delete(slots[4]) == 0
    assert not store.exists(slots[4])
    assert store.exists(slots[5])
    with pytest.raises(SlotNotFoundError):
        store.read(slots[4])

    reloaded = FileFrameStore(tmp_path)
    reloaded.load_index()
    assert reloaded.entries() == store.entries()
    assert reloaded.total_bytes() == store.total_bytes()

    for slot in slots:
        reloaded.delete(slot)
    assert reloaded.entries() == []
    assert list((tmp_path / "frames").iterdir()) == []


def test_temp_files_are_ignored_and_stale_ones_cleaned(tmp_path: Path) -> None:
    store = FileFrameStore(tmp_path)
    store.write(make_frame(NOW))
    day_dir = store.path_for(NOW).parent
    stale = day_dir / ".tmp-stale"
    fresh = day_dir / ".tmp-fresh.mfr"
    stale.write_bytes(b"partial")
    fresh.write_bytes(b"partial")
    misplaced = day_dir.parent / store.path_for(NOW - FIVE_MIN).name
    misplaced.write_bytes(store.path_for(NOW).read_bytes())
    two_hours_ago = time.time() - 7200
    os.utime(stale, (two_hours_ago, two_hours_ago))

    reloaded = FileFrameStore(tmp_path)
    reloaded.load_index()

    assert [e.slot for e in reloaded.entries()] == [NOW]
    assert not stale.exists()
    assert fresh.exists()


def test_maintenance_drops_an_unreadable_frame_it_must_downgrade(tmp_path: Path) -> None:
    store = FileFrameStore(tmp_path)
    old = NOW - timedelta(days=35)
    store.write(make_frame(old))
    path = store.path_for(old)
    data = path.read_bytes()
    path.write_bytes(data[: len(data) - 20])
    store.write(make_frame(old + timedelta(hours=3)))
    maintenance = Maintenance(store, FileLayerCache(tmp_path), FixedClock(NOW), STYLE, BIG_CAP)

    report = maintenance.run()

    assert report.downgraded == 1
    assert [e.slot for e in store.entries()] == [old + timedelta(hours=3)]
    assert not path.exists()
    assert not maintenance.run().changed


def _seeded(slot: datetime) -> bool:
    """Two frames per 3-hour bucket past 30 days, two per hour every 6 h after that."""
    if slot <= NOW - timedelta(days=30):
        return (slot.minute, slot.hour % 3) in {(0, 0), (30, 1)}
    return slot.hour % 6 == 0


def seed_forty_days(store: FileFrameStore) -> None:
    """Frames across 40 days, every 5 min over the last 3 h, and one missed HH:00."""
    missed_hour = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    start = datetime(2026, 8, 21, 0, 0, tzinfo=UTC)
    for slot in slots_every(start, NOW - timedelta(hours=3), timedelta(minutes=30)):
        if _seeded(slot) and slot != missed_hour:
            store.write(make_frame(slot))
    store.write(make_frame(missed_hour + FIVE_MIN))
    for slot in slots_every(NOW - timedelta(hours=3) + FIVE_MIN, NOW + FIVE_MIN, FIVE_MIN):
        store.write(make_frame(slot))


def put_layer(cache: FileLayerCache, slot: datetime, size: int, mtime: float) -> Path:
    cache.put(STYLE, slot, b"\x89PNG" + bytes(size - 4))
    path = cache.path_for(STYLE, slot)
    os.utime(path, (mtime, mtime))
    return path


def test_maintenance_thins_downgrades_caps_and_is_idempotent(tmp_path: Path) -> None:
    store = FileFrameStore(tmp_path)
    store.load_index()
    cache = FileLayerCache(tmp_path)
    seed_forty_days(store)
    maintenance = Maintenance(store, cache, FixedClock(NOW), STYLE, BIG_CAP)

    first = maintenance.run()

    slots = [e.slot for e in store.entries()]
    assert first.thinned > 0
    assert first.downgraded == MAX_DOWNGRADES_PER_RUN
    assert first.dropped_for_cap == 0
    by_tier: dict[Tier, list[datetime]] = {tier: [] for tier in Tier}
    for slot in slots:
        by_tier[tier_of(slot, NOW)].append(slot)
    assert len(by_tier[Tier.FIVE_MIN]) == 36
    replaced_hour = datetime(2026, 9, 20, 12, 5, tzinfo=UTC)
    assert replaced_hour in by_tier[Tier.HOURLY]
    assert all(s.minute == 0 for s in by_tier[Tier.HOURLY] if s != replaced_hour)
    hourly_buckets = [s.replace(minute=0) for s in by_tier[Tier.HOURLY]]
    assert len(hourly_buckets) == len(set(hourly_buckets))
    assert all(s.minute == 0 and s.hour % 3 == 0 for s in by_tier[Tier.THREE_HOURLY])
    assert len(by_tier[Tier.THREE_HOURLY]) == 84
    downgraded = [e.slot for e in store.entries() if e.kind is FrameKind.CLASS_U8]
    assert downgraded == by_tier[Tier.THREE_HOURLY][:MAX_DOWNGRADES_PER_RUN]

    runs = 1
    while maintenance.run().downgraded:
        runs += 1
    assert runs == 4
    kinds = {e.slot: e.kind for e in store.entries()}
    assert all(kinds[s] is FrameKind.CLASS_U8 for s in by_tier[Tier.THREE_HOURLY])
    assert all(kinds[s] is FrameKind.ACRR_U16 for s in by_tier[Tier.HOURLY])

    settled = store.entries()
    assert not maintenance.run().changed
    assert store.entries() == settled


def test_maintenance_cap_drops_oldest_and_holds_layer_budget(tmp_path: Path) -> None:
    store = FileFrameStore(tmp_path)
    store.load_index()
    cache = FileLayerCache(tmp_path)
    for slot in slots_every(NOW - timedelta(days=2), NOW - timedelta(hours=3), timedelta(hours=1)):
        store.write(make_frame(slot))
    entries = store.entries()
    sizes = [e.size for e in entries]
    total = sum(sizes)
    cap = int((total - sum(sizes[:5])) / 0.9)
    frame_budget = cap - int(cap * 0.1)
    layer_budget = int(cap * 0.1)
    expected_drop = next(k for k in range(len(sizes)) if total - sum(sizes[:k]) <= frame_budget)

    layer_size = layer_budget // 3 + 1
    base = time.time() - 1000
    layers = [put_layer(cache, e.slot, layer_size, base + i) for i, e in enumerate(entries[-5:])]
    orphan_future = put_layer(cache, NOW + timedelta(hours=1), 8, base + 10)
    orphan_dropped = put_layer(cache, entries[0].slot, 8, base + 11)
    other_style = FileLayerCache(tmp_path)
    other_style.put("aaaa", NOW, b"\x89PNG1234")

    assert cache.purge_other_styles(STYLE) == 8
    assert not (tmp_path / "layers" / "aaaa").exists()
    with pytest.raises(StyleNotFoundError):
        cache.path_for("../frames", NOW)

    maintenance = Maintenance(store, cache, FixedClock(NOW), STYLE, cap)
    report = maintenance.run()

    assert expected_drop >= 5
    assert report.dropped_for_cap == expected_drop
    assert [e.slot for e in store.entries()] == [e.slot for e in entries[expected_drop:]]
    assert store.total_bytes() <= frame_budget
    assert report.layer_bytes_freed == 3 * layer_size
    assert [p.exists() for p in layers] == [False, False, False, True, True]
    assert report.orphan_layers == 2
    assert not orphan_future.exists()
    assert not orphan_dropped.exists()
    assert cache.total_bytes() == 2 * layer_size <= layer_budget
    assert (tmp_path / "frames").is_dir()
    assert tmp_path.is_dir()

    assert not maintenance.run().changed
