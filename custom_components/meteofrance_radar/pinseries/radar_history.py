"""RadarPinHistory: rain rate of the home cell over the recent radar archive.

The rain bar asks for the last three hours on every refresh. Reading a stored frame
decodes a 3,472 x 3,472 raster, so each slot is read once and its pin value kept in
memory until it falls out of the window. Everything here is blocking and runs in the
executor.
"""

from __future__ import annotations

import logging
import math
import threading
from datetime import datetime
from typing import Final

from ..decode.pin import radar_cell
from ..domain.models import AcrrFrame, FrameKind, SourceGrid
from ..domain.ports import FrameStore
from ..domain.rate import acrr_rate
from ..errors import FrameFormatError, InvalidProductError, SlotNotFoundError

_LOGGER = logging.getLogger(__name__)
# Products share one source grid; a second one covers a grid change in the archive.
MAX_GRIDS: Final = 2

type Cell = tuple[int, int] | None
type PinValue = tuple[datetime, float | None]


class RadarPinHistory:
    """Per-slot rain rate at one WGS84 point, cached for the current source cell.

    Args:
        store: The frame store the collector writes to.
    """

    def __init__(self, store: FrameStore) -> None:
        self._store = store
        self._lock = threading.Lock()
        self._pin: tuple[float, float] | None = None
        self._grids: dict[str, SourceGrid] = {}
        self._cells: dict[str, Cell] = {}
        self._values: dict[datetime, float | None] = {}

    def values(self, lon: float, lat: float, start: datetime, end: datetime) -> list[PinValue]:
        """Rain rate in mm/h at (lon, lat) for every lossless frame in [start, end).

        None means no data at that cell (nodata, or the point is outside the radar
        grid); undetect reads as 0.0. Downgraded (class_u8) frames are skipped, and so
        is a frame that cannot be read, which is retried on the next call. Values of
        slots before `start` are dropped from the cache.
        """
        with self._lock:
            self._use_pin(lon, lat)
            self._values = {s: v for s, v in self._values.items() if s >= start}
            result: list[PinValue] = []
            for entry in self._store.entries_between(start, end):
                if entry.kind is not FrameKind.ACRR_U16:
                    continue
                if entry.slot not in self._values:
                    frame = self._read(entry.slot)
                    if frame is None:
                        continue
                    self._values[entry.slot] = self._rate_at(frame, lon, lat)
                result.append((entry.slot, self._values[entry.slot]))
            return result

    def _use_pin(self, lon: float, lat: float) -> None:
        """Switch to a new point, clearing the cache when its cell differs."""
        if self._pin == (lon, lat):
            return
        self._pin = (lon, lat)
        cells = {key: _cell_of(grid, lon, lat) for key, grid in self._grids.items()}
        if cells != self._cells:
            self._values.clear()
        self._cells = cells

    def _cell(self, grid: SourceGrid, lon: float, lat: float) -> Cell:
        key = grid.key()
        if key not in self._cells:
            if len(self._grids) >= MAX_GRIDS:
                self._grids.clear()
                self._cells.clear()
            self._grids[key] = grid
            self._cells[key] = _cell_of(grid, lon, lat)
        return self._cells[key]

    def _read(self, slot: datetime) -> AcrrFrame | None:
        """Lossless frame of a slot, None when it cannot be used now."""
        try:
            frame = self._store.read(slot)
        except (SlotNotFoundError, FrameFormatError, OSError) as err:
            _LOGGER.debug("Cannot read the frame of %s for the pin: %s", slot, err)
            return None
        return frame if isinstance(frame, AcrrFrame) else None

    def _rate_at(self, frame: AcrrFrame, lon: float, lat: float) -> float | None:
        """Rain rate in mm/h of the point's cell, None for no data."""
        cell = self._cell(frame.grid, lon, lat)
        if cell is None:
            return None
        row, col = cell
        rate = float(acrr_rate(frame.raw[row : row + 1, col : col + 1], frame.scaling)[0, 0])
        return None if math.isnan(rate) else rate


def _cell_of(grid: SourceGrid, lon: float, lat: float) -> Cell:
    """Source cell of a point, None outside the grid or for an unsupported projection."""
    try:
        return radar_cell(grid, lon, lat)
    except InvalidProductError:
        return None
