"""FileLayerCache: rendered PNG layers under layers/<style>/<slot>.png, held to a byte budget.

Layers are regenerable from the stored frames, so every deletion here is safe. Only the
layers directory is ever read or deleted.
"""

from __future__ import annotations

import contextlib
import re
import shutil
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from ..domain.slots import format_slot, parse_slot
from ..errors import StyleNotFoundError
from .atomic import atomic_write_bytes, is_temp_file, remove_stale_temp_files

LAYERS_SUBDIR: Final = "layers"
LAYER_SUFFIX: Final = ".png"
_STYLE_PATTERN: Final = re.compile(r"[0-9a-f]{1,64}")


@dataclass(frozen=True)
class _CachedLayer:
    path: Path
    size: int
    mtime: float


def _dir_bytes(directory: Path) -> int:
    total = 0
    for path in directory.rglob("*"):
        with contextlib.suppress(FileNotFoundError):
            if path.is_file():
                total += path.stat().st_size
    return total


class FileLayerCache:
    """LayerCache on the local filesystem.

    Args:
        root: The storage root; layers live under root/layers.
    """

    def __init__(self, root: Path) -> None:
        self._base = root / LAYERS_SUBDIR

    def _style_dir(self, style: str) -> Path:
        if _STYLE_PATTERN.fullmatch(style) is None:
            raise StyleNotFoundError(f"invalid layer style {style!r}")
        return self._base / style

    def path_for(self, style: str, slot: datetime) -> Path:
        """Path of the cached layer of a style and slot.

        Raises:
            StyleNotFoundError: style is not a lowercase hex id, so it never names a path
                outside the cache.
        """
        return self._style_dir(style) / f"{format_slot(slot)}{LAYER_SUFFIX}"

    def get(self, style: str, slot: datetime) -> bytes | None:
        """Cached PNG, or None on a miss."""
        try:
            return self.path_for(style, slot).read_bytes()
        except FileNotFoundError:
            return None

    def put(self, style: str, slot: datetime, png: bytes) -> None:
        """Cache a PNG atomically.

        Raises:
            OSError: the write failed.
        """
        atomic_write_bytes(self.path_for(style, slot), png)

    def purge_other_styles(self, style: str) -> int:
        """Remove every style directory but style, and stale temporary files.

        Returns:
            Bytes freed.
        """
        self._style_dir(style)
        if not self._base.is_dir():
            return 0
        freed = 0
        for entry in self._base.iterdir():
            if entry.is_dir() and entry.name != style:
                freed += _dir_bytes(entry)
                shutil.rmtree(entry, ignore_errors=True)
        remove_stale_temp_files(self._base)
        return freed

    def _layers(self) -> list[_CachedLayer]:
        found: list[_CachedLayer] = []
        if not self._base.is_dir():
            return found
        for path in self._base.glob(f"*/*{LAYER_SUFFIX}"):
            if is_temp_file(path):
                continue
            with contextlib.suppress(FileNotFoundError):
                stat = path.stat()
                found.append(_CachedLayer(path, stat.st_size, stat.st_mtime))
        return found

    def enforce_budget(self, budget_bytes: int) -> int:
        """Delete layers, oldest modification time first, until they fit in budget_bytes.

        Returns:
            Bytes freed.
        """
        layers = sorted(self._layers(), key=lambda layer: (layer.mtime, layer.path.name))
        total = sum(layer.size for layer in layers)
        freed = 0
        for layer in layers:
            if total <= budget_bytes:
                break
            with contextlib.suppress(FileNotFoundError):
                layer.path.unlink()
                freed += layer.size
            total -= layer.size
        return freed

    def remove_orphans(self, style: str, keep: Collection[datetime]) -> int:
        """Delete the layers of style whose slot is not in keep (their frame is gone).

        Files whose name is not a slot are removed too: nothing could ever serve them.

        Returns:
            Number of files deleted.
        """
        directory = self._style_dir(style)
        if not directory.is_dir():
            return 0
        deleted = 0
        for path in directory.glob(f"*{LAYER_SUFFIX}"):
            if is_temp_file(path):
                continue
            try:
                slot: datetime | None = parse_slot(path.name.removesuffix(LAYER_SUFFIX))
            except ValueError:
                slot = None
            if slot is None or slot not in keep:
                with contextlib.suppress(FileNotFoundError):
                    path.unlink()
                    deleted += 1
        return deleted

    def total_bytes(self) -> int:
        """Size of every cached layer, every style included."""
        return sum(layer.size for layer in self._layers())
