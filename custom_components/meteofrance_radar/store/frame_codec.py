"""The .mfr frame container: magic, version, JSON header, xz-compressed payload.

Layout (little-endian):

    offset 0   4 bytes   magic b"MFRF"
    offset 4   1 byte    format version
    offset 5   4 bytes   header length N, uint32
    offset 9   N bytes   header, UTF-8 JSON with sorted keys
    offset 9+N           payload, compressed with stdlib lzma (xz container, preset 6)

An acrr_u16 payload is the row-major uint16 array byte-shuffled (every low byte, then every
high byte) before compression, which roughly halves the size of rain fields. A class_u8
payload is the row-major uint8 array as is. Grid corners are stored as a list so their order
survives the sorted-key JSON.
"""

from __future__ import annotations

import json
import lzma
import struct
from typing import Any, BinaryIO, Final

import numpy as np
from numpy.typing import NDArray

from ..domain.models import AcrrFrame, ClassFrame, Frame, FrameKind, Scaling, SourceGrid
from ..domain.palette import NODATA_INDEX
from ..domain.slots import format_slot, parse_slot
from ..errors import FrameFormatError

MAGIC: Final = b"MFRF"
FORMAT_VERSION: Final = 1
CODEC_XZ: Final = "xz"
XZ_PRESET: Final = 6

_PREFIX = struct.Struct("<4sBI")
PREFIX_SIZE: Final = _PREFIX.size
_SHUFFLE = {FrameKind.ACRR_U16: 2, FrameKind.CLASS_U8: 1}
_DTYPES: dict[FrameKind, np.dtype[Any]] = {
    FrameKind.ACRR_U16: np.dtype("<u2"),
    FrameKind.CLASS_U8: np.dtype("u1"),
}


def _grid_header(grid: SourceGrid) -> dict[str, Any]:
    return {
        "projdef": grid.projdef,
        "xsize": grid.xsize,
        "ysize": grid.ysize,
        "xscale": grid.xscale,
        "yscale": grid.yscale,
        "corners": [[name, x, y] for name, x, y in grid.corners],
    }


def _header_of(frame: Frame) -> tuple[dict[str, Any], NDArray[Any]]:
    grid = _grid_header(frame.grid)
    kind = kind_of(frame)
    if isinstance(frame, AcrrFrame):
        s = frame.scaling
        array: NDArray[Any] = frame.raw
        extra: dict[str, Any] = {
            "scaling": {
                "gain": s.gain,
                "offset": s.offset,
                "nodata": s.nodata,
                "undetect": s.undetect,
            }
        }
    else:
        array = frame.idx
        extra = {"classes": {"levels_mmh": list(frame.levels_mmh), "nodata_index": NODATA_INDEX}}
    header = {
        "slot": format_slot(frame.slot),
        "kind": kind.value,
        "shape": list(array.shape),
        "codec": CODEC_XZ,
        "shuffle": _SHUFFLE[kind],
        "grid": grid,
        **extra,
    }
    return header, np.ascontiguousarray(array, dtype=_DTYPES[kind])


def encode_frame(frame: Frame) -> bytes:
    """Serialise a frame to the .mfr container."""
    header, array = _header_of(frame)
    raw = array.view(np.uint8)
    if header["shuffle"] == 2:
        raw = raw.reshape(-1, 2).T
    payload = lzma.compress(raw.tobytes(), preset=XZ_PRESET)
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    return _PREFIX.pack(MAGIC, FORMAT_VERSION, len(header_bytes)) + header_bytes + payload


def decode_header(data: bytes) -> tuple[dict[str, Any], int]:
    """Parse the prefix and JSON header.

    Args:
        data: The file content, or at least its first 9 + N bytes.

    Returns:
        The header and the offset where the payload starts.

    Raises:
        FrameFormatError: bad magic, version, header length or header JSON.
    """
    if len(data) < PREFIX_SIZE:
        raise FrameFormatError("frame file shorter than its prefix")
    magic, version, length = _PREFIX.unpack_from(data)
    if magic != MAGIC:
        raise FrameFormatError(f"bad frame magic {magic!r}")
    if version != FORMAT_VERSION:
        raise FrameFormatError(f"unsupported frame format version {version}")
    end = PREFIX_SIZE + length
    if len(data) < end:
        raise FrameFormatError(f"frame header length {length} runs past the end of the file")
    try:
        header = json.loads(data[PREFIX_SIZE:end])
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise FrameFormatError(f"unreadable frame header: {err}") from err
    if not isinstance(header, dict):
        raise FrameFormatError("frame header is not a JSON object")
    return header, end


def read_header(handle: BinaryIO) -> dict[str, Any]:
    """Read only the prefix and header of an open .mfr file, not its payload.

    Raises:
        FrameFormatError: bad magic, version, header length or header JSON.
    """
    prefix = handle.read(PREFIX_SIZE)
    if len(prefix) < PREFIX_SIZE:
        raise FrameFormatError("frame file shorter than its prefix")
    _, _, length = _PREFIX.unpack(prefix)
    header, _ = decode_header(prefix + handle.read(length))
    return header


def kind_of(frame: Frame) -> FrameKind:
    """Storage kind of a frame."""
    return FrameKind.ACRR_U16 if isinstance(frame, AcrrFrame) else FrameKind.CLASS_U8


def header_kind(header: dict[str, Any]) -> FrameKind:
    """Frame kind named by a header.

    Raises:
        FrameFormatError: unknown kind.
    """
    try:
        return FrameKind(str(header.get("kind")))
    except ValueError as err:
        raise FrameFormatError(f"unknown frame kind {header.get('kind')!r}") from err


def _payload_array(header: dict[str, Any], payload: bytes, kind: FrameKind) -> NDArray[Any]:
    if header.get("codec") != CODEC_XZ:
        raise FrameFormatError(f"unsupported frame codec {header.get('codec')!r}")
    if header.get("shuffle") != _SHUFFLE[kind]:
        raise FrameFormatError(f"bad shuffle {header.get('shuffle')!r} for {kind.value}")
    shape = tuple(int(n) for n in header["shape"])
    if len(shape) != 2 or min(shape) <= 0:
        raise FrameFormatError(f"frame shape {shape} is not a 2D grid")
    dtype = _DTYPES[kind]
    try:
        raw = lzma.decompress(payload, format=lzma.FORMAT_XZ)
    except lzma.LZMAError as err:
        raise FrameFormatError(f"corrupt frame payload: {err}") from err
    if len(raw) != int(np.prod(shape)) * dtype.itemsize:
        raise FrameFormatError(f"payload of {len(raw)} bytes does not match shape {shape}")
    flat = np.frombuffer(raw, dtype=np.uint8)
    if dtype.itemsize == 2:
        flat = np.ascontiguousarray(flat.reshape(2, -1).T)
    return flat.view(dtype).reshape(shape).astype(dtype.newbyteorder("="), copy=True)


def _source_grid(grid: dict[str, Any]) -> SourceGrid:
    return SourceGrid(
        projdef=str(grid["projdef"]),
        xsize=int(grid["xsize"]),
        ysize=int(grid["ysize"]),
        xscale=float(grid["xscale"]),
        yscale=float(grid["yscale"]),
        corners=tuple((str(n), float(x), float(y)) for n, x, y in grid["corners"]),
    )


def _build(header: dict[str, Any], payload: bytes) -> Frame:
    kind = header_kind(header)
    array = _payload_array(header, payload, kind)
    slot = parse_slot(header["slot"])
    grid = _source_grid(header["grid"])
    if kind is FrameKind.ACRR_U16:
        s = header["scaling"]
        scaling = Scaling(
            gain=float(s["gain"]),
            offset=float(s["offset"]),
            nodata=float(s["nodata"]),
            undetect=float(s["undetect"]),
        )
        return AcrrFrame(slot=slot, grid=grid, scaling=scaling, raw=array)
    levels = tuple(float(v) for v in header["classes"]["levels_mmh"])
    return ClassFrame(slot=slot, grid=grid, levels_mmh=levels, idx=array)


def decode_frame(data: bytes) -> Frame:
    """Parse a .mfr container back into the frame it was encoded from.

    Raises:
        FrameFormatError: any mismatch in magic, version, header, codec or payload length.
    """
    header, start = decode_header(data)
    try:
        return _build(header, data[start:])
    except (KeyError, TypeError, ValueError) as err:
        raise FrameFormatError(f"incomplete frame header: {err!r}") from err
