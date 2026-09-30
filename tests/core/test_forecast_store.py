"""Forecast store on a real directory: staging, commits, pruning, reload and pin series."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from custom_components.meteofrance_radar.domain.forecast import (
    ForecastProduct,
    PiafRun,
    PiafStep,
    PinSeries,
    PinValue,
)
from custom_components.meteofrance_radar.store.atomic import TEMP_PREFIX
from custom_components.meteofrance_radar.store.forecast_store import FileForecastStore

STYLE = "style00001"
RUN_A = datetime(2026, 9, 30, 14, 30, tzinfo=UTC)
RUN_B = RUN_A + timedelta(minutes=15)
RUN_C = RUN_B + timedelta(minutes=15)
PIN = (2.46, 48.80)


def _png(run: datetime, lead: int) -> bytes:
    return f"png {run:%H%M} +{lead}".encode()


def _commit(store: FileForecastStore, run: datetime, leads: tuple[int, ...] = (5, 10)) -> PiafRun:
    store.begin_run(run)
    for lead in leads:
        store.stage_layer(run, run + timedelta(minutes=lead), _png(run, lead))
    piaf = PiafRun(
        run=run,
        style=STYLE,
        steps=tuple(PiafStep(run + timedelta(minutes=lead), lead, 0.5) for lead in leads),
        pin=PIN,
    )
    store.commit_run(piaf)
    return piaf


def _run_dirs(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "forecast" / "piaf").iterdir())


def _temp_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.name.startswith(TEMP_PREFIX)]


def test_commit_replace_keeps_current_and_previous_only(tmp_path: Path) -> None:
    store = FileForecastStore(tmp_path)
    store.load(STYLE)

    first = _commit(store, RUN_A)
    assert store.current_piaf() == first
    assert store.staged(RUN_A) == []
    assert store.read_layer(RUN_A, RUN_A + timedelta(minutes=5)) == _png(RUN_A, 5)

    _commit(store, RUN_B)
    third = _commit(store, RUN_C)

    assert store.current_piaf() == third
    assert _run_dirs(tmp_path) == ["20260930T1445Z", "20260930T1500Z"]
    assert store.read_layer(RUN_B, RUN_B + timedelta(minutes=10)) == _png(RUN_B, 10)
    assert store.read_layer(RUN_A, RUN_A + timedelta(minutes=5)) is None
    assert store.read_layer(RUN_C, RUN_C + timedelta(minutes=15)) is None
    assert store.total_bytes() > 0
    assert _temp_files(tmp_path) == []


def test_recommitting_the_same_run_replaces_it(tmp_path: Path) -> None:
    store = FileForecastStore(tmp_path)
    store.load(STYLE)
    _commit(store, RUN_A)
    _commit(store, RUN_B)

    again = _commit(store, RUN_B, leads=(5, 10, 15))

    assert store.current_piaf() == again
    assert _run_dirs(tmp_path) == ["20260930T1430Z", "20260930T1445Z"]
    assert store.read_layer(RUN_B, RUN_B + timedelta(minutes=15)) == _png(RUN_B, 15)


def test_staging_is_resumable_and_restarted_by_begin(tmp_path: Path) -> None:
    store = FileForecastStore(tmp_path)
    store.load(STYLE)
    store.begin_run(RUN_A)
    store.stage_layer(RUN_A, RUN_A + timedelta(minutes=10), b"b")
    store.stage_layer(RUN_A, RUN_A + timedelta(minutes=5), b"a")

    assert store.staged(RUN_A) == [RUN_A + timedelta(minutes=5), RUN_A + timedelta(minutes=10)]
    store.begin_run(RUN_B)
    assert store.staged(RUN_A) == []
    assert store.staged(RUN_B) == []
    with pytest.raises(FileNotFoundError):
        store.stage_layer(RUN_A, RUN_A, b"x")
    with pytest.raises(FileNotFoundError):
        store.commit_run(PiafRun(RUN_A, STYLE, (), None))


def test_load_drops_staging_other_styles_and_older_runs(tmp_path: Path) -> None:
    store = FileForecastStore(tmp_path)
    store.load(STYLE)
    _commit(store, RUN_A)
    _commit(store, RUN_B)
    store.begin_run(RUN_C)
    store.stage_layer(RUN_C, RUN_C + timedelta(minutes=5), b"partial")
    (tmp_path / "forecast" / "piaf" / "20260930T1400Z").mkdir()
    (tmp_path / "forecast" / "piaf" / "20260930T1415Z").mkdir()
    (tmp_path / "forecast" / "piaf" / "20260930T1415Z" / "run.json").write_text("{broken")

    reloaded = FileForecastStore(tmp_path)
    reloaded.load(STYLE)

    assert _run_dirs(tmp_path) == ["20260930T1430Z", "20260930T1445Z"]
    current = reloaded.current_piaf()
    assert current is not None
    assert current.run == RUN_B
    assert current.pin == PIN
    assert reloaded.read_layer(RUN_A, RUN_A + timedelta(minutes=5)) == _png(RUN_A, 5)

    FileForecastStore(tmp_path).load("otherstyle")
    assert _run_dirs(tmp_path) == []


def test_pin_series_round_trip_and_corrupt_file(tmp_path: Path) -> None:
    store = FileForecastStore(tmp_path)
    store.load(STYLE)
    series = PinSeries(
        product=ForecastProduct.AROMEPI,
        run=RUN_A,
        lon=PIN[0],
        lat=PIN[1],
        values=(PinValue(RUN_A + timedelta(minutes=15), 0.4296875),),
    )

    store.save_pin_series(series)
    (tmp_path / "forecast" / "pins" / "arome.json").write_text('{"product": "arome"}')
    reloaded = FileForecastStore(tmp_path)
    reloaded.load(STYLE)

    assert store.pin_series(ForecastProduct.AROMEPI) == series
    assert reloaded.pin_series(ForecastProduct.AROMEPI) == series
    assert reloaded.pin_series(ForecastProduct.AROME) is None
    assert not (tmp_path / "forecast" / "pins" / "arome.json").exists()
    assert _temp_files(tmp_path) == []
