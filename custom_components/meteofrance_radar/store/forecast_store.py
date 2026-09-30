"""Forecast files: the latest PIAF run's layers and the pin series of AROME-PI and AROME.

Layout under <storage root>/forecast:

    piaf/<RUN>/<VALID>.png      layers of a committed run (RUN, VALID = YYYYMMDDTHHMMZ)
    piaf/<RUN>/run.json         steps, style and pin of that run
    piaf/.staging-<RUN>/        a run being fetched; removed at load
    pins/<product>.json         latest pin series of a product

Only the current run and the one it replaced are kept: a card that listed the frames
just before a commit still finds its layers. Nothing here counts toward the size cap.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from ..domain.forecast import ForecastProduct, PiafRun, PiafStep, PinSeries, PinValue
from .atomic import atomic_write_bytes, is_temp_file

_LOGGER = logging.getLogger(__name__)

FORECAST_SUBDIR: Final = "forecast"
PIAF_SUBDIR: Final = "piaf"
PINS_SUBDIR: Final = "pins"
STAGING_PREFIX: Final = ".staging-"
RUN_MANIFEST: Final = "run.json"
LAYER_SUFFIX: Final = ".png"
NAME_FORMAT: Final = "%Y%m%dT%H%MZ"
ISO_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"


def _name(t: datetime) -> str:
    return t.astimezone(UTC).strftime(NAME_FORMAT)


def _parse_name(text: str) -> datetime | None:
    try:
        return datetime.strptime(text, NAME_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime(ISO_FORMAT)


def _parse_iso(text: Any) -> datetime:
    if not isinstance(text, str):
        raise ValueError(f"expected an ISO time, got {text!r}")
    return datetime.strptime(text, ISO_FORMAT).replace(tzinfo=UTC)


def _run_to_json(piaf: PiafRun) -> bytes:
    document = {
        "run": _iso(piaf.run),
        "style": piaf.style,
        "pin": None if piaf.pin is None else [piaf.pin[0], piaf.pin[1]],
        "steps": [
            {"valid": _iso(step.valid), "lead_min": step.lead_min, "pin_mm_h": step.pin_mm_h}
            for step in piaf.steps
        ],
    }
    return json.dumps(document, separators=(",", ":")).encode()


def _run_from_json(data: bytes) -> PiafRun:
    document = json.loads(data)
    pin = document["pin"]
    return PiafRun(
        run=_parse_iso(document["run"]),
        style=str(document["style"]),
        steps=tuple(
            PiafStep(
                valid=_parse_iso(step["valid"]),
                lead_min=int(step["lead_min"]),
                pin_mm_h=None if step["pin_mm_h"] is None else float(step["pin_mm_h"]),
            )
            for step in document["steps"]
        ),
        pin=None if pin is None else (float(pin[0]), float(pin[1])),
    )


def _remove_tree(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        _LOGGER.warning("Could not delete forecast directory %s: %s", path.name, exc)


def _series_to_json(series: PinSeries) -> bytes:
    document = {
        "product": series.product.value,
        "run": _iso(series.run),
        "lon": series.lon,
        "lat": series.lat,
        "values": [[_iso(value.valid), value.mm_h] for value in series.values],
    }
    return json.dumps(document, separators=(",", ":")).encode()


def _series_from_json(data: bytes) -> PinSeries:
    document = json.loads(data)
    return PinSeries(
        product=ForecastProduct(document["product"]),
        run=_parse_iso(document["run"]),
        lon=float(document["lon"]),
        lat=float(document["lat"]),
        values=tuple(PinValue(_parse_iso(t), float(v)) for t, v in document["values"]),
    )


class FileForecastStore:
    """Forecast files under root/forecast, thread-safe (the ForecastStore port).

    Args:
        root: The storage root; forecast files live under root/forecast.
    """

    def __init__(self, root: Path) -> None:
        self._base = root / FORECAST_SUBDIR
        self._piaf_dir = self._base / PIAF_SUBDIR
        self._pins_dir = self._base / PINS_SUBDIR
        self._lock = threading.RLock()
        self._current: PiafRun | None = None
        self._previous: datetime | None = None
        self._pins: dict[ForecastProduct, PinSeries] = {}

    def _run_dir(self, run: datetime) -> Path:
        return self._piaf_dir / _name(run)

    def _staging_dir(self, run: datetime) -> Path:
        return self._piaf_dir / f"{STAGING_PREFIX}{_name(run)}"

    def _remove_staging(self) -> None:
        for path in self._piaf_dir.glob(f"{STAGING_PREFIX}*"):
            _remove_tree(path)

    def _read_run(self, path: Path) -> PiafRun | None:
        try:
            return _run_from_json((path / RUN_MANIFEST).read_bytes())
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            _LOGGER.warning("Dropping unreadable forecast run %s: %s", path.name, exc)
            return None

    def _load_runs(self, style: str) -> list[PiafRun]:
        runs = []
        for path in sorted(self._piaf_dir.iterdir()):
            if not path.is_dir() or path.name.startswith(STAGING_PREFIX):
                continue
            run = self._read_run(path)
            if run is None or run.style != style or path.name != _name(run.run):
                _remove_tree(path)
                continue
            runs.append(run)
        return sorted(runs, key=lambda item: item.run)

    def _load_pins(self) -> None:
        self._pins = {}
        for product in ForecastProduct:
            path = self._pins_dir / f"{product.value}.json"
            if not path.exists():
                continue
            try:
                series = _series_from_json(path.read_bytes())
            except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
                _LOGGER.warning("Dropping unreadable pin series %s: %s", path.name, exc)
                path.unlink(missing_ok=True)
                continue
            if series.product is product:
                self._pins[product] = series

    def _prune_runs(self) -> None:
        keep = {_name(run) for run in (self._current_run(), self._previous) if run}
        for path in self._piaf_dir.iterdir():
            if path.is_dir() and not path.name.startswith(STAGING_PREFIX) and path.name not in keep:
                _remove_tree(path)

    def _current_run(self) -> datetime | None:
        return None if self._current is None else self._current.run

    def load(self, style: str) -> None:
        """Create the directories, drop staging, other styles and stale runs, read the rest."""
        with self._lock:
            self._piaf_dir.mkdir(parents=True, exist_ok=True)
            self._pins_dir.mkdir(parents=True, exist_ok=True)
            self._remove_staging()
            runs = self._load_runs(style)
            self._current = runs[-1] if runs else None
            self._previous = runs[-2].run if len(runs) > 1 else None
            self._prune_runs()
            self._load_pins()

    def current_piaf(self) -> PiafRun | None:
        """The latest committed PIAF run, from memory."""
        with self._lock:
            return self._current

    def begin_run(self, run: datetime) -> None:
        """Start staging `run` from scratch, dropping any other staging."""
        with self._lock:
            self._piaf_dir.mkdir(parents=True, exist_ok=True)
            self._remove_staging()
            self._staging_dir(run).mkdir()

    def stage_layer(self, run: datetime, valid: datetime, png: bytes) -> None:
        """Write the layer of one step into the staging of `run`.

        Raises:
            FileNotFoundError: `run` is not being staged.
        """
        with self._lock:
            staging = self._staging_dir(run)
            if not staging.is_dir():
                raise FileNotFoundError(f"forecast run {_name(run)} is not being staged")
            atomic_write_bytes(staging / f"{_name(valid)}{LAYER_SUFFIX}", png)

    def staged(self, run: datetime) -> list[datetime]:
        """Valid times already staged for `run`, ascending; empty when not staging it."""
        with self._lock:
            staging = self._staging_dir(run)
            if not staging.is_dir():
                return []
            times = (
                _parse_name(path.stem)
                for path in staging.glob(f"*{LAYER_SUFFIX}")
                if not is_temp_file(path)
            )
            return sorted(t for t in times if t is not None)

    def commit_run(self, piaf: PiafRun) -> None:
        """Publish the staged run, then keep only it and the run it replaces.

        Raises:
            FileNotFoundError: `piaf.run` is not being staged.
        """
        with self._lock:
            staging = self._staging_dir(piaf.run)
            if not staging.is_dir():
                raise FileNotFoundError(f"forecast run {_name(piaf.run)} is not being staged")
            atomic_write_bytes(staging / RUN_MANIFEST, _run_to_json(piaf))
            target = self._run_dir(piaf.run)
            if target.exists():
                shutil.rmtree(target)
            os.replace(staging, target)
            replaced = self._current
            if replaced is not None and replaced.run != piaf.run:
                self._previous = replaced.run
            self._current = piaf
            self._prune_runs()

    def read_layer(self, run: datetime, valid: datetime) -> bytes | None:
        """Layer PNG of the current or previous run; None for any other run or a missing step."""
        with self._lock:
            if run not in (self._current_run(), self._previous):
                return None
            path = self._run_dir(run) / f"{_name(valid)}{LAYER_SUFFIX}"
            try:
                return path.read_bytes()
            except FileNotFoundError:
                return None

    def pin_series(self, product: ForecastProduct) -> PinSeries | None:
        """Saved pin series of a product, from memory."""
        with self._lock:
            return self._pins.get(product)

    def save_pin_series(self, series: PinSeries) -> None:
        """Atomically replace the saved pin series of its product."""
        with self._lock:
            atomic_write_bytes(
                self._pins_dir / f"{series.product.value}.json", _series_to_json(series)
            )
            self._pins[series.product] = series

    def total_bytes(self) -> int:
        """Total size of the forecast files."""
        with self._lock:
            if not self._base.is_dir():
                return 0
            return sum(p.stat().st_size for p in self._base.rglob("*") if p.is_file())
