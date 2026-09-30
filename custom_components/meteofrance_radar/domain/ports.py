"""Interfaces through which adapters plug into the use cases (no I/O here)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .forecast import BBox, CoverageTimes, ForecastProduct, PiafRun, PinSeries
from .models import Frame, FrameEntry


class Clock(Protocol):
    """Source of the current time."""

    def now(self) -> datetime:
        """Return the current aware UTC time."""
        ...


class ProductSource(Protocol):
    """Remote source serving only the latest product (async, the aiohttp client)."""

    async def latest_validity_time(self) -> datetime:
        """Validity time of the latest product in the catalogue.

        Raises:
            ApiAuthError: the key is refused.
            ApiError: any other failure.
        """
        ...

    async def download_latest(self) -> bytes:
        """Download the latest product file (ODIM HDF5 bytes).

        Raises:
            ApiAuthError: the key is refused.
            ApiError: any other failure.
        """
        ...


class FrameStore(Protocol):
    """Stored frames, one file per slot (sync, called in the executor)."""

    def load_index(self) -> None:
        """Scan the disk once and build the in-memory index."""
        ...

    def entries(self) -> list[FrameEntry]:
        """Every stored frame, ascending by slot, from memory."""
        ...

    def entries_between(self, start: datetime, end: datetime) -> list[FrameEntry]:
        """Stored frames with a slot in [start, end), ascending, from memory."""
        ...

    def exists(self, slot: datetime) -> bool:
        """Return True when a frame is stored for the slot."""
        ...

    def write(self, frame: Frame) -> FrameEntry:
        """Atomically write a frame, replacing any frame of the same slot."""
        ...

    def read(self, slot: datetime) -> Frame:
        """Read the frame of a slot.

        Raises:
            SlotNotFoundError: no frame for the slot.
            FrameFormatError: the file is corrupt or of an unknown format.
        """
        ...

    def delete(self, slot: datetime) -> int:
        """Delete the frame of a slot; return the bytes freed, 0 when absent."""
        ...

    def total_bytes(self) -> int:
        """Total size of the stored frames."""
        ...


class LayerCache(Protocol):
    """Disk cache of rendered layer PNGs, keyed by style and slot."""

    def get(self, style: str, slot: datetime) -> bytes | None:
        """Cached PNG, or None on a miss."""
        ...

    def put(self, style: str, slot: datetime, png: bytes) -> None:
        """Cache a PNG."""
        ...

    def purge_other_styles(self, style: str) -> int:
        """Delete every layer of another style; return the bytes freed."""
        ...

    def enforce_budget(self, budget_bytes: int) -> int:
        """Delete oldest-mtime layers until under budget; return the bytes freed."""
        ...

    def total_bytes(self) -> int:
        """Total size of the cached layers."""
        ...


class CoverageSource(Protocol):
    """One forecast WCS API (async, the aiohttp WcsClient)."""

    async def describe(self, coverage_id: str) -> CoverageTimes | None:
        """Valid times of a run, or None when the run is not published yet (404).

        Raises:
            ApiAuthError: the key is refused (401 or 403).
            ApiError: any other failure.
        """
        ...

    async def get_grib(self, coverage_id: str, valid: datetime, bbox: BBox) -> bytes:
        """GRIB2 bytes of one valid time of a coverage, cut to `bbox`.

        Raises:
            ApiAuthError: the key is refused (401 or 403).
            ApiError: any other failure, or a body that is not GRIB.
        """
        ...


class ForecastStore(Protocol):
    """Latest PIAF run layers and pin series on disk (sync, called in the executor)."""

    def load(self, style: str) -> None:
        """Create the directories, drop staging and stale runs, read what is kept."""
        ...

    def current_piaf(self) -> PiafRun | None:
        """The latest committed PIAF run, from memory."""
        ...

    def begin_run(self, run: datetime) -> None:
        """Start staging `run` from scratch, dropping any other staging."""
        ...

    def stage_layer(self, run: datetime, valid: datetime, png: bytes) -> None:
        """Write the layer of one step into the staging of `run`."""
        ...

    def staged(self, run: datetime) -> list[datetime]:
        """Valid times already staged for `run`, ascending."""
        ...

    def commit_run(self, piaf: PiafRun) -> None:
        """Publish the staged run; keep only it and the run it replaces."""
        ...

    def read_layer(self, run: datetime, valid: datetime) -> bytes | None:
        """Layer PNG of the current or previous run, None otherwise or when missing."""
        ...

    def pin_series(self, product: ForecastProduct) -> PinSeries | None:
        """Saved pin series of a product, from memory."""
        ...

    def save_pin_series(self, series: PinSeries) -> None:
        """Atomically replace the saved pin series of its product."""
        ...

    def total_bytes(self) -> int:
        """Total size of the forecast files."""
        ...
