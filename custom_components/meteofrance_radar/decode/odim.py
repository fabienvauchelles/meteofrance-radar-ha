"""h5py adapter reading Météo-France ODIM_H5 lame d'eau composites into AcrrFrame.

The product is read from memory and never touches disk. Only the ACRR data, its scaling
and the georeferencing are kept: the QIND quality layer is ignored on purpose, since
every cell is shown. Any deviation from the expected structure raises
InvalidProductError, so a silent format change on the Météo-France side cannot
produce a misplaced or misscaled frame.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import h5py
import numpy as np
from numpy.typing import NDArray

from ..domain.models import AcrrFrame, Scaling, SourceGrid
from ..domain.slots import is_slot
from ..errors import InvalidProductError
from .stereo import parse_projdef

DATA_PATH = "/dataset1/data1/data"
DATA_WHAT_PATH = "/dataset1/data1/what"
DATASET_WHAT_PATH = "/dataset1/what"
WHERE_PATH = "/where"
EXPECTED_SIZE = 3472
EXPECTED_SHAPE = (EXPECTED_SIZE, EXPECTED_SIZE)
EXPECTED_QUANTITY = "ACRR"
CORNER_NAMES = ("UL", "UR", "LL", "LR")
_TIME_FORMAT = "%Y%m%d%H%M%S"


def _text(value: Any) -> str:
    if isinstance(value, bytes | np.bytes_):
        return bytes(value).decode("utf-8").strip("\x00").strip()
    return str(value).strip()


@contextmanager
def _open(data: bytes) -> Iterator[Any]:
    """Open HDF5 bytes in memory, mapping read failures to InvalidProductError."""
    if not data:
        raise InvalidProductError("empty product")
    try:
        handle = h5py.File.in_memory(data)
    except (OSError, ValueError) as exc:
        raise InvalidProductError("not a readable HDF5 file", cause=str(exc)) from exc
    with handle:
        yield handle


def _read_slot(handle: Any) -> datetime:
    try:
        what = handle[DATASET_WHAT_PATH].attrs
        text = _text(what["enddate"]) + _text(what["endtime"])
        slot = datetime.strptime(text, _TIME_FORMAT).replace(tzinfo=UTC)
    except (KeyError, OSError, ValueError) as exc:
        raise InvalidProductError(
            "slot unreadable from /dataset1/what enddate/endtime", cause=str(exc)
        ) from exc
    if not is_slot(slot):
        raise InvalidProductError("slot not on the 5-minute grid", slot=slot)
    return slot


def _read_grid(handle: Any, slot: datetime) -> SourceGrid:
    try:
        where = handle[WHERE_PATH].attrs
        corners = tuple(
            (name, float(where[f"{name}_lon"]), float(where[f"{name}_lat"]))
            for name in CORNER_NAMES
        )
        grid = SourceGrid(
            projdef=_text(where["projdef"]),
            xsize=int(where["xsize"]),
            ysize=int(where["ysize"]),
            xscale=float(where["xscale"]),
            yscale=float(where["yscale"]),
            corners=corners,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidProductError(
            "georeferencing missing or malformed in /where", slot=slot, cause=str(exc)
        ) from exc
    if (grid.ysize, grid.xsize) != EXPECTED_SHAPE or grid.xscale <= 0 or grid.yscale <= 0:
        raise InvalidProductError(
            "unexpected /where size or scale",
            slot=slot,
            cause=f"{grid.xsize}x{grid.ysize} cells of {grid.xscale}x{grid.yscale} m",
        )
    parse_projdef(grid.projdef)
    return grid


def _read_scaling(handle: Any, slot: datetime) -> Scaling:
    try:
        what = handle[DATA_WHAT_PATH].attrs
        quantity = _text(what["quantity"])
        scaling = Scaling(
            gain=float(what["gain"]),
            offset=float(what["offset"]),
            nodata=float(what["nodata"]),
            undetect=float(what["undetect"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidProductError(
            "scaling missing or malformed in /dataset1/data1/what", slot=slot, cause=str(exc)
        ) from exc
    if quantity != EXPECTED_QUANTITY:
        raise InvalidProductError(
            "unsupported quantity", slot=slot, cause=f"{quantity!r} != {EXPECTED_QUANTITY!r}"
        )
    if not np.isfinite([scaling.gain, scaling.offset]).all() or scaling.gain <= 0:
        raise InvalidProductError("invalid gain or offset", slot=slot, cause=str(scaling))
    return scaling


def _read_raw(handle: Any, slot: datetime) -> NDArray[np.uint16]:
    if DATA_PATH not in handle:
        raise InvalidProductError(f"missing {DATA_PATH}", slot=slot)
    dataset = handle[DATA_PATH]
    if not isinstance(dataset, h5py.Dataset):
        raise InvalidProductError(f"{DATA_PATH} is not a dataset", slot=slot)
    if dataset.dtype != np.uint16 or tuple(dataset.shape) != EXPECTED_SHAPE:
        raise InvalidProductError(
            "unexpected data layout",
            slot=slot,
            cause=f"{dataset.dtype} {tuple(dataset.shape)} != uint16 {EXPECTED_SHAPE}",
        )
    raw: NDArray[np.uint16] = np.ascontiguousarray(dataset[()], dtype=np.uint16)
    return raw


def read_product(data: bytes) -> AcrrFrame:
    """Decode a 500 m lame d'eau product from its HDF5 bytes.

    The slot is the end of the accumulation, from /dataset1/what enddate and endtime.

    Raises:
        InvalidProductError: not readable HDF5, no valid slot, quantity other than ACRR,
            data other than uint16 3472x3472, or malformed scaling or georeferencing.
        UnsupportedProjectionError: projdef the numpy projection cannot handle.
    """
    with _open(data) as handle:
        slot = _read_slot(handle)
        # h5py reads lazily: a truncated file can fail on any later attribute or chunk.
        try:
            grid = _read_grid(handle, slot)
            scaling = _read_scaling(handle, slot)
            raw = _read_raw(handle, slot)
        except OSError as exc:
            raise InvalidProductError("product unreadable", slot=slot, cause=str(exc)) from exc
    return AcrrFrame(slot=slot, grid=grid, scaling=scaling, raw=raw)
