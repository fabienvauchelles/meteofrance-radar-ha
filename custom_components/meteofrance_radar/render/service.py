"""Layer use case: serve a cached layer, or render one and cache it.

Cache hits never take the render lock. Misses render one layer at a time per process,
which bounds memory: a render holds the 24 MB frame, the 19 MB table and the gathered
arrays, and several concurrent ones would add up on a small board.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from ..decode.reproject import TableCache
from ..domain.grid import TargetGrid
from ..domain.ports import FrameStore, LayerCache
from ..errors import FrameFormatError, InvalidProductError, SlotNotFoundError, StyleNotFoundError
from .layer import render_layer

_LOGGER = logging.getLogger(__name__)


class LayerService:
    """Return layer PNG bytes for a (style, slot) pair.

    Args:
        store: Frame store the layers are rendered from.
        cache: Rendered layer cache.
        tables: Reprojection tables, shared by every render of this process.
        grid: Target grid of every layer.
        style: Current style id, the only one served.
    """

    def __init__(
        self,
        store: FrameStore,
        cache: LayerCache,
        tables: TableCache,
        grid: TargetGrid,
        style: str,
    ) -> None:
        self._store = store
        self._cache = cache
        self._tables = tables
        self._grid = grid
        self._style = style
        self._render_lock = threading.Lock()

    @property
    def style(self) -> str:
        """The current style id, part of every layer URL."""
        return self._style

    def get_layer(self, style: str, slot: datetime) -> bytes:
        """Return the layer PNG for `slot`. Blocking: call it in the executor.

        Raises:
            StyleNotFoundError: `style` is not the current style.
            SlotNotFoundError: no frame is stored for `slot`, including one deleted by
                maintenance while it was being rendered.
            InvalidProductError: the stored frame cannot be decoded or rendered.
        """
        if style != self._style:
            raise StyleNotFoundError(f"unknown layer style {style!r}")
        cached = self._cache.get(style, slot)
        if cached is not None:
            return cached
        if not self._store.exists(slot):
            raise SlotNotFoundError("no frame stored for slot", slot=slot)
        with self._render_lock:
            cached = self._cache.get(style, slot)
            if cached is not None:
                return cached
            started = time.perf_counter()
            png = self._render(slot)
            _LOGGER.debug(
                "Rendered layer %s (style %s) in %.3f s",
                slot.isoformat(),
                style,
                time.perf_counter() - started,
            )
            try:
                self._cache.put(style, slot, png)
            except OSError as exc:
                # A full or read-only disk must not stop the layer from being served.
                _LOGGER.warning("Could not cache layer %s: %s", slot.isoformat(), exc)
            return png

    def _render(self, slot: datetime) -> bytes:
        try:
            frame = self._store.read(slot)
            return render_layer(frame, self._tables.get(frame.grid, self._grid))
        except (FrameFormatError, InvalidProductError) as exc:
            if not self._store.exists(slot):
                raise SlotNotFoundError("frame deleted while rendering", slot=slot) from None
            if isinstance(exc, InvalidProductError):
                raise
            raise InvalidProductError("stored frame unreadable", slot=slot, cause=str(exc)) from exc
