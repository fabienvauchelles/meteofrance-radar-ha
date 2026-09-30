"""Atomic file writes: unique temporary file in the target directory, fsync, then rename."""

from __future__ import annotations

import contextlib
import os
import tempfile
import time
from pathlib import Path

TEMP_PREFIX = ".tmp-"
STALE_TEMP_AGE_S = 3600.0


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write data to path so that readers never see a partial file.

    Parent directories are created. The temporary file lives next to path (same filesystem,
    so os.replace is atomic) and is removed if anything fails.

    Raises:
        OSError: the directory cannot be created or the write fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=TEMP_PREFIX)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()
        raise


def is_temp_file(path: Path) -> bool:
    """Return True when path is a temporary file left by atomic_write_bytes."""
    return path.name.startswith(TEMP_PREFIX)


def remove_stale_temp_files(base: Path, max_age_s: float = STALE_TEMP_AGE_S) -> int:
    """Delete temporary files under base older than max_age_s (an interrupted write).

    Recent ones are kept: another writer may still be about to rename them.

    Returns:
        Number of files deleted.
    """
    if not base.is_dir():
        return 0
    cutoff = time.time() - max_age_s
    deleted = 0
    for path in base.rglob(f"{TEMP_PREFIX}*"):
        with contextlib.suppress(FileNotFoundError):
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
    return deleted
