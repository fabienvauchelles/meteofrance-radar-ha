"""Tiered retention driven by real collector passes over frames seeded across 40 days.

Seeded frames are small (their content does not matter to retention) but carry the real
source grid and scaling, so the downgrade to class indices runs the production code.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.meteofrance_radar.const import CONF_SIZE_CAP_MB
from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.domain.models import AcrrFrame, FrameEntry, FrameKind
from custom_components.meteofrance_radar.store.frame_store import FileFrameStore
from tests.support.mf_api import FIXTURE_SLOT, dry_product, mock_api
from tests.support.setup import NOW, async_setup_integration, async_tick

HOUR = timedelta(hours=1)
FIVE_MIN = timedelta(minutes=5)
DAY = timedelta(days=1)
SEED_SHAPE = (16, 16)
HEAVY_SHAPE = (256, 256)


@pytest.fixture(autouse=True)
def _frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(NOW)


def _every(start: datetime, end: datetime, step: timedelta) -> list[datetime]:
    slots = []
    slot = start
    while slot <= end:
        slots.append(slot)
        slot += step
    return slots


def _seed(root: Path, slots: Iterable[datetime], shape: tuple[int, int], high: int) -> None:
    template = read_product(dry_product(FIXTURE_SLOT))
    rng = np.random.default_rng(7)
    store = FileFrameStore(root)
    for slot in slots:
        raw = rng.integers(0, high, size=shape, dtype=np.uint16)
        store.write(AcrrFrame(slot=slot, grid=template.grid, scaling=template.scaling, raw=raw))


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def _kinds(entries: list[FrameEntry], start: datetime, end: datetime) -> dict[datetime, FrameKind]:
    return {e.slot: e.kind for e in entries if start <= e.slot <= end}


async def test_passes_thin_and_downgrade_frames_as_they_age(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
) -> None:
    root = tmp_path / "radar"
    recent = [
        s
        for s in _every(_at("2026-09-30T05:00"), _at("2026-09-30T10:25"), FIVE_MIN)
        if s != _at("2026-09-30T06:00")
    ]
    month_old = _every(_at("2026-08-30T08:00"), _at("2026-09-01T12:00"), HOUR)
    older = [
        day + offset
        for day in _every(_at("2026-08-21T00:00"), _at("2026-08-29T00:00"), DAY)
        for offset in (timedelta(0), HOUR)
    ]
    await hass.async_add_executor_job(_seed, root, [*older, *month_old, *recent], SEED_SHAPE, 3000)
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))

    entry = await async_setup_integration(hass, root)
    store = entry.runtime_data.store
    entries = store.entries()

    three_hourly = _kinds(entries, _at("2026-08-01T00:00"), _at("2026-08-31T10:30"))
    assert sorted(three_hourly) == [
        *_every(_at("2026-08-21T00:00"), _at("2026-08-29T00:00"), DAY),
        _at("2026-08-30T08:00"),
        *_every(_at("2026-08-30T09:00"), _at("2026-08-31T09:00"), 3 * HOUR),
    ]
    assert set(three_hourly.values()) == {FrameKind.CLASS_U8}
    hourly_old = _kinds(entries, _at("2026-08-31T11:00"), _at("2026-09-01T12:00"))
    assert sorted(hourly_old) == _every(_at("2026-08-31T11:00"), _at("2026-09-01T12:00"), HOUR)
    assert set(hourly_old.values()) == {FrameKind.ACRR_U16}
    assert sorted(_kinds(entries, _at("2026-09-30T05:00"), _at("2026-09-30T07:30"))) == [
        _at("2026-09-30T05:00"),
        _at("2026-09-30T06:05"),
        _at("2026-09-30T07:00"),
    ]
    assert sorted(_kinds(entries, _at("2026-09-30T07:35"), _at("2026-09-30T10:30"))) == (
        _every(_at("2026-09-30T07:35"), _at("2026-09-30T10:30"), FIVE_MIN)
    )

    next_slot = FIXTURE_SLOT + HOUR
    mock_api(aioclient_mock, next_slot, dry_product(next_slot))
    await async_tick(hass, freezer, HOUR)
    entries = store.entries()

    assert entries[-1].slot == next_slot
    assert _at("2026-08-31T11:00") not in _kinds(entries, _at("2026-08-31T11:00"), next_slot)
    assert _at("2026-08-31T12:00") in _kinds(entries, _at("2026-08-31T12:00"), next_slot)
    assert sorted(_kinds(entries, _at("2026-09-30T07:00"), _at("2026-09-30T08:30"))) == [
        _at("2026-09-30T07:00"),
        _at("2026-09-30T08:00"),
    ]


async def test_size_cap_drops_the_oldest_frames_first(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Path
) -> None:
    root = tmp_path / "radar"
    seeded = [_at("2026-09-02T12:00") + 2 * i * DAY for i in range(12)]
    await hass.async_add_executor_job(_seed, root, seeded, HEAVY_SHAPE, 65_000)
    mock_api(aioclient_mock, FIXTURE_SLOT, dry_product(FIXTURE_SLOT))

    entry = await async_setup_integration(hass, root, options={CONF_SIZE_CAP_MB: 1})
    store = entry.runtime_data.store
    slots = [e.slot for e in store.entries()]

    frame_budget = 900_000
    assert store.total_bytes() <= frame_budget
    assert slots[-1] == FIXTURE_SLOT
    kept = slots[:-1]
    assert kept == seeded[len(seeded) - len(kept) :]
    assert 0 < len(kept) < len(seeded)
    heaviest = max(e.size for e in store.entries())
    assert store.total_bytes() + heaviest > frame_budget
