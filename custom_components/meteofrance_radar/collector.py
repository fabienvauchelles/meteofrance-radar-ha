"""One collector pass: catalogue, download, decode, store, then maintenance.

The pass is written over ports and plain callables so it holds no Home Assistant
object: the glue hands it the API client, the frame store, the decoder, a free-space
probe, the maintenance job and a way to run blocking work in the executor. The raw
HDF5 bytes only live in memory for the length of one pass; they never touch disk.
"""

from __future__ import annotations

import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import Protocol

from .const import LOGGER, MIN_FREE_BYTES
from .domain.models import AcrrFrame
from .domain.ports import FrameStore, ProductSource
from .errors import InvalidProductError

SLOT_FORMAT = "%Y%m%dT%H%MZ"


class BlockingRunner(Protocol):
    """Runs a blocking callable off the event loop and awaits its result."""

    def __call__[T](self, func: Callable[[], T], /) -> Awaitable[T]: ...


class PassOutcome(StrEnum):
    """What one collector pass did."""

    UNCHANGED = "unchanged"
    STORED = "stored"
    SKIPPED = "skipped"
    SKIPPED_DISK = "skipped_disk"
    FAILED = "failed"


@dataclass(frozen=True)
class CollectorState:
    """Result of the last completed pass, kept as the coordinator data."""

    last_pass: datetime
    outcome: PassOutcome
    last_stored_slot: datetime | None
    last_error: str | None


def free_bytes(root: Path) -> int:
    """Free space on the file system holding ``root``, in bytes."""
    return shutil.disk_usage(root).free


def slot_text(slot: datetime) -> str:
    """Slot as ``YYYYMMDDTHHMMZ`` for log lines."""
    return slot.astimezone(UTC).strftime(SLOT_FORMAT)


class Collector:
    """Polls the latest product and stores it under its own slot.

    Args:
        source: Remote product source (catalogue validity time and download).
        store: Frame store, only called from the executor.
        decode: Reads an ODIM HDF5 product from memory; raises InvalidProductError.
        free_space: Returns the free bytes on the storage root.
        maintain: Thinning, downgrade and cap enforcement, run after a stored frame.
        run_blocking: Runs a blocking callable in the executor.
        min_free_bytes: Below this free space, a new frame is not written.
    """

    def __init__(
        self,
        source: ProductSource,
        store: FrameStore,
        decode: Callable[[bytes], AcrrFrame],
        free_space: Callable[[], int],
        maintain: Callable[[], object],
        run_blocking: BlockingRunner,
        min_free_bytes: int = MIN_FREE_BYTES,
    ) -> None:
        self._source = source
        self._store = store
        self._decode = decode
        self._free_space = free_space
        self._maintain = maintain
        self._run_blocking = run_blocking
        self._min_free_bytes = min_free_bytes
        self._last_handled: datetime | None = None
        self._last_stored: datetime | None = None

    async def run_pass(self, now: datetime) -> CollectorState:
        """Run one pass and return its state.

        Raises:
            ApiAuthError: the key was refused.
            ApiError: the catalogue or the download failed.
            OSError: the store could not be written.
        """
        validity = await self._source.latest_validity_time()
        if validity == self._last_handled:
            LOGGER.debug("unchanged validity_time=%s", slot_text(validity))
            return self._state(now, PassOutcome.UNCHANGED)
        data = await self._source.download_latest()
        outcome, slot, error = await self._run_blocking(partial(self._ingest, data))
        if slot is not None:
            self._compare(validity, slot)
        if outcome is PassOutcome.STORED:
            self._last_stored = slot
            await self._run_blocking(self._maintain)
        return self._state(now, outcome, error)

    def _ingest(self, data: bytes) -> tuple[PassOutcome, datetime | None, str | None]:
        try:
            frame = self._decode(data)
        except InvalidProductError as exc:
            LOGGER.error("invalid product: %s", exc)
            return PassOutcome.FAILED, None, f"{type(exc).__name__}: {exc}"
        slot = frame.slot
        if self._store.exists(slot):
            LOGGER.debug("skipped slot=%s, already stored", slot_text(slot))
            return PassOutcome.SKIPPED, slot, None
        free = self._free_space()
        if free < self._min_free_bytes:
            LOGGER.warning(
                "free space %d bytes below %d, slot=%s not written",
                free,
                self._min_free_bytes,
                slot_text(slot),
            )
            return PassOutcome.SKIPPED_DISK, slot, "free space below the minimum"
        entry = self._store.write(frame)
        LOGGER.debug("stored slot=%s bytes=%d", slot_text(slot), entry.size)
        return PassOutcome.STORED, slot, None

    def _compare(self, validity: datetime, slot: datetime) -> None:
        if slot >= validity:
            self._last_handled = validity
        if slot > validity:
            LOGGER.warning(
                "superseded validity_time=%s slot=%s", slot_text(validity), slot_text(slot)
            )
        elif slot < validity:
            LOGGER.warning("stale validity_time=%s slot=%s", slot_text(validity), slot_text(slot))

    def _state(
        self, now: datetime, outcome: PassOutcome, error: str | None = None
    ) -> CollectorState:
        return CollectorState(
            last_pass=now,
            outcome=outcome,
            last_stored_slot=self._last_stored,
            last_error=error,
        )
