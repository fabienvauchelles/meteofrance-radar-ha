"""Maintenance use case: tier thinning, downgrade, size cap and layer budget.

Runs in the executor after each stored frame and at setup, never concurrently with itself
(the coordinator serialises passes). It deletes files only through the store and the layer
cache, so the storage root itself is never removed.
"""

from __future__ import annotations

import logging
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Protocol

from ..domain.models import AcrrFrame, FrameKind
from ..domain.ports import Clock, FrameStore, LayerCache
from ..domain.rate import to_class_frame
from ..domain.tiers import needs_downgrade, plan_thinning
from ..errors import FrameFormatError, SlotNotFoundError

MAX_DOWNGRADES_PER_RUN: Final = 24
DEFAULT_LAYER_SHARE: Final = 0.10

_LOGGER = logging.getLogger(__name__)


class PrunableLayerCache(LayerCache, Protocol):
    """A LayerCache that can also drop the layers of frames that no longer exist."""

    def remove_orphans(self, style: str, keep: Collection[datetime]) -> int: ...


@dataclass(frozen=True)
class MaintenanceReport:
    """What one run changed; all zero when the storage was already in shape."""

    thinned: int
    downgraded: int
    dropped_for_cap: int
    layer_bytes_freed: int
    orphan_layers: int

    @property
    def changed(self) -> bool:
        """True when the run deleted or rewrote anything."""
        return any(
            (
                self.thinned,
                self.downgraded,
                self.dropped_for_cap,
                self.layer_bytes_freed,
                self.orphan_layers,
            )
        )


class Maintenance:
    """Keeps the stored frames in their tiers and the whole storage under its cap.

    Args:
        store: The frame store (index already loaded).
        layers: The rendered layer cache.
        clock: Source of "now" for tier ages.
        style: The current layer style; orphans are looked for in its directory.
        cap_bytes: Total size cap for frames plus layers.
        layer_share: Share of the cap reserved to rendered layers.
    """

    def __init__(
        self,
        store: FrameStore,
        layers: PrunableLayerCache,
        clock: Clock,
        style: str,
        cap_bytes: int,
        layer_share: float = DEFAULT_LAYER_SHARE,
    ) -> None:
        self._store = store
        self._layers = layers
        self._clock = clock
        self._style = style
        self._layer_budget = int(cap_bytes * layer_share)
        self._frame_budget = cap_bytes - self._layer_budget

    def run(self, now: datetime | None = None) -> MaintenanceReport:
        """Thin, downgrade, enforce the cap, then hold the layer cache to its budget.

        Args:
            now: Reference time for tier ages; the clock when omitted.

        Raises:
            OSError: a file operation failed.
        """
        at = now if now is not None else self._clock.now()
        thinned = self._thin(at)
        downgraded = self._downgrade(at)
        dropped = self._enforce_frame_budget()
        layer_freed = self._layers.enforce_budget(self._layer_budget)
        keep = {entry.slot for entry in self._store.entries()}
        orphans = self._layers.remove_orphans(self._style, keep)
        report = MaintenanceReport(thinned, downgraded, dropped, layer_freed, orphans)
        if report.changed:
            _LOGGER.debug("storage maintenance: %s", report)
        return report

    def _thin(self, now: datetime) -> int:
        slots = [entry.slot for entry in self._store.entries()]
        doomed = list(plan_thinning(slots, now))
        for slot in doomed:
            self._store.delete(slot)
        return len(doomed)

    def _downgrade(self, now: datetime) -> int:
        done = 0
        for entry in self._store.entries():
            if done >= MAX_DOWNGRADES_PER_RUN:
                break
            if entry.kind is not FrameKind.ACRR_U16 or not needs_downgrade(entry.slot, now):
                continue
            try:
                frame = self._store.read(entry.slot)
            except SlotNotFoundError:
                continue
            except FrameFormatError as err:
                # An unreadable frame can never be served; keeping it would repeat this
                # warning on every run until the cap finally dropped it.
                _LOGGER.warning("dropping unreadable frame %s: %s", entry.slot.isoformat(), err)
                self._store.delete(entry.slot)
                continue
            if isinstance(frame, AcrrFrame):
                self._store.write(to_class_frame(frame))
                done += 1
        return done

    def _enforce_frame_budget(self) -> int:
        dropped = 0
        entries = self._store.entries()
        total = self._store.total_bytes()
        for entry in entries:
            if total <= self._frame_budget:
                break
            self._store.delete(entry.slot)
            total -= entry.size
            dropped += 1
        return dropped
