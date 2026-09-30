"""FileFrameStore: one .mfr file per slot under frames/YYYY/MM/DD/, indexed in memory.

The disk is scanned once by load_index. Every writer lives in this process and goes through
write and delete, which keep the index current, so readers (the frames view) never touch the
disk to list frames.
"""

from __future__ import annotations

import bisect
import contextlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Final

from ..domain.models import Frame, FrameEntry
from ..domain.slots import format_slot, parse_slot
from ..errors import FrameFormatError, SlotNotFoundError
from .atomic import atomic_write_bytes, is_temp_file, remove_stale_temp_files
from .frame_codec import (
    decode_frame,
    encode_frame,
    header_kind,
    kind_of,
    read_header,
)

FRAMES_SUBDIR: Final = "frames"
FRAME_SUFFIX: Final = ".mfr"


def frame_slot_of(path: Path) -> datetime | None:
    """Slot named by a frame file, or None for anything else (temporary files included)."""
    name = path.name
    if is_temp_file(path) or not name.endswith(FRAME_SUFFIX):
        return None
    try:
        return parse_slot(name.removesuffix(FRAME_SUFFIX))
    except ValueError:
        return None


class FileFrameStore:
    """FrameStore on the local filesystem.

    Args:
        root: The storage root; frames live under root/frames.
    """

    def __init__(self, root: Path) -> None:
        self._base = root / FRAMES_SUBDIR
        self._lock = threading.Lock()
        self._slots: list[datetime] = []
        self._entries: dict[datetime, FrameEntry] = {}

    @property
    def base(self) -> Path:
        """Directory holding the frame tree."""
        return self._base

    def path_for(self, slot: datetime) -> Path:
        """Path of the file of a slot, whether it exists or not."""
        name = format_slot(slot)
        return self._base / name[0:4] / name[4:6] / name[6:8] / f"{name}{FRAME_SUFFIX}"

    def load_index(self) -> None:
        """Scan the tree into the index and delete temporary files older than an hour.

        Files whose header cannot be read are left in place and out of the index.

        Raises:
            OSError: the tree cannot be listed.
        """
        remove_stale_temp_files(self._base)
        found: dict[datetime, FrameEntry] = {}
        if self._base.is_dir():
            for path in self._base.rglob(f"*{FRAME_SUFFIX}"):
                entry = self._scan(path)
                if entry is not None:
                    found[entry.slot] = entry
        with self._lock:
            self._entries = found
            self._slots = sorted(found)

    def _scan(self, path: Path) -> FrameEntry | None:
        slot = frame_slot_of(path)
        # A file outside its slot folder could never be read or deleted through path_for.
        if slot is None or path != self.path_for(slot) or not path.is_file():
            return None
        try:
            with path.open("rb") as handle:
                kind = header_kind(read_header(handle))
            size = path.stat().st_size
        except OSError, FrameFormatError:
            return None
        return FrameEntry(slot=slot, kind=kind, size=size)

    def entries(self) -> list[FrameEntry]:
        """Every stored frame, ascending by slot."""
        with self._lock:
            return [self._entries[slot] for slot in self._slots]

    def entries_between(self, start: datetime, end: datetime) -> list[FrameEntry]:
        """Stored frames with start <= slot < end, ascending."""
        with self._lock:
            lo = bisect.bisect_left(self._slots, start)
            hi = bisect.bisect_left(self._slots, end)
            return [self._entries[slot] for slot in self._slots[lo:hi]]

    def exists(self, slot: datetime) -> bool:
        """Return True when a frame is stored for the slot."""
        with self._lock:
            return slot in self._entries

    def write(self, frame: Frame) -> FrameEntry:
        """Store a frame atomically, replacing any frame of the same slot.

        Raises:
            OSError: the write failed (no partial file is left).
        """
        data = encode_frame(frame)
        atomic_write_bytes(self.path_for(frame.slot), data)
        entry = FrameEntry(slot=frame.slot, kind=kind_of(frame), size=len(data))
        with self._lock:
            if frame.slot not in self._entries:
                bisect.insort(self._slots, frame.slot)
            self._entries[frame.slot] = entry
        return entry

    def read(self, slot: datetime) -> Frame:
        """Decode the frame of a slot.

        Raises:
            SlotNotFoundError: no frame for the slot.
            FrameFormatError: the file is not a valid .mfr container.
        """
        if not self.exists(slot):
            raise SlotNotFoundError("no frame stored", slot=slot)
        try:
            data = self.path_for(slot).read_bytes()
        except FileNotFoundError as err:
            raise SlotNotFoundError("frame file missing", slot=slot) from err
        return decode_frame(data)

    def delete(self, slot: datetime) -> int:
        """Delete the frame of a slot and its emptied directories.

        Returns:
            Bytes freed, 0 when no frame was stored.
        """
        path = self.path_for(slot)
        with self._lock:
            entry = self._entries.pop(slot, None)
            if entry is not None:
                del self._slots[bisect.bisect_left(self._slots, slot)]
        freed = 0
        with contextlib.suppress(FileNotFoundError):
            freed = path.stat().st_size
            path.unlink()
        self._prune_dirs(path.parent)
        return freed

    def _prune_dirs(self, directory: Path) -> None:
        """Remove empty day, month and year directories; never the frames base itself."""
        for _ in range(3):
            if directory == self._base or self._base not in directory.parents:
                return
            try:
                directory.rmdir()
            except OSError:
                return
            directory = directory.parent

    def total_bytes(self) -> int:
        """Size of every indexed frame file."""
        with self._lock:
            return sum(entry.size for entry in self._entries.values())
