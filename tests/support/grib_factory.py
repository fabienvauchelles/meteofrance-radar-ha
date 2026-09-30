"""Synthetic GRIB2 messages: the exact inverse of decode.grib for simple packing.

Values are packed with R = min(values) and X = rint((value - R) / 2**e), so values on
the 2**e grid above R round-trip exactly. Arguments outside what the decoder supports
(bitmap 0, packing template 3, 12 bits, edition 1, grid template 1, scan 64) still
produce well-formed bytes, so each refusal can be tested on its own.
"""

from __future__ import annotations

import struct

import numpy as np
from numpy.typing import ArrayLike, NDArray

MICRO = 1_000_000
_MISSING_U32 = 0xFFFFFFFF


def _sign_magnitude(value: int, bits: int) -> int:
    return (1 << (bits - 1)) | -value if value < 0 else value


def _section(number: int, body: bytes) -> bytes:
    return struct.pack(">IB", len(body) + 5, number) + body


def _section3(
    ni: int,
    nj: int,
    lon0: float,
    lat0: float,
    dlon: float,
    dlat: float,
    *,
    template3: int,
    scan: int,
) -> bytes:
    lo1 = round((lon0 % 360.0) * MICRO)
    la1 = round(lat0 * MICRO)
    la2 = round((lat0 - (nj - 1) * dlat) * MICRO)
    lo2 = round(((lon0 + (ni - 1) * dlon) % 360.0) * MICRO)
    body = struct.pack(">BIBBH", 0, ni * nj, 0, 0, template3)
    body += struct.pack(">BBIBIBI", 6, 255, _MISSING_U32, 255, _MISSING_U32, 255, _MISSING_U32)
    body += struct.pack(">IIII", ni, nj, 0, _MISSING_U32)
    body += struct.pack(">II", _sign_magnitude(la1, 32), _sign_magnitude(lo1, 32))
    body += struct.pack(">B", 0x30)
    body += struct.pack(">II", _sign_magnitude(la2, 32), _sign_magnitude(lo2, 32))
    body += struct.pack(">IIB", round(dlon * MICRO), round(dlat * MICRO), scan)
    return _section(3, body)


def _pack_bits(raw: NDArray[np.uint64], bits: int) -> bytes:
    if bits == 0:
        return b""
    shifts = np.arange(bits - 1, -1, -1, dtype=np.uint64)
    flat = ((raw[:, None] >> shifts) & np.uint64(1)).astype(np.uint8).ravel()
    return np.packbits(flat).tobytes()


def write_grib2(
    values: ArrayLike,
    *,
    lon0: float,
    lat0: float,
    dlon: float,
    dlat: float,
    e: int = -12,
    bits: int = 16,
    bitmap: int = 255,
    template5: int = 0,
    template3: int = 0,
    edition: int = 2,
    scan: int = 0,
    truncate_data: int = 0,
) -> bytes:
    """One GRIB2 message holding `values` (shape (nj, ni), row 0 north) on a lat/lon grid.

    Args:
        values: Field values; row 0 is north, column 0 west.
        lon0, lat0: Centre of cell (0, 0) in degrees.
        dlon, dlat: Positive cell spacing in degrees.
        e: Binary scale factor E.
        bits: Bits per packed value; 0 writes a constant field of value min(values).
        bitmap: Bitmap indicator of section 6 (0 appends an all-present bitmap).
        template5, template3: Data representation and grid template numbers.
        edition: GRIB edition byte of section 0.
        scan: Scanning mode byte of section 3.
        truncate_data: Bytes cut from the end of the packed data.
    """
    field = np.asarray(values, dtype=np.float64)
    nj, ni = field.shape
    reference = float(np.float32(field.min()))
    raw = np.rint((field.ravel() - reference) / 2.0**e).astype(np.uint64)
    if bits and int(raw.max()) >= 1 << bits:
        raise ValueError(f"values need more than {bits} bits at e={e}")
    section1 = _section(1, bytes(16))
    section3 = _section3(ni, nj, lon0, lat0, dlon, dlat, template3=template3, scan=scan)
    section4 = _section(4, bytes(29))
    body5 = struct.pack(">IH", ni * nj, template5) + struct.pack(">f", reference)
    body5 += struct.pack(">HHBB", _sign_magnitude(e, 16), 0, bits, 0)
    section5 = _section(5, body5)
    bitmap_bytes = np.packbits(np.ones(ni * nj, dtype=np.uint8)).tobytes() if bitmap == 0 else b""
    section6 = _section(6, bytes([bitmap]) + bitmap_bytes)
    data = _pack_bits(raw, bits)
    section7 = _section(7, data[: len(data) - truncate_data])
    sections = section1 + section3 + section4 + section5 + section6 + section7
    total = 16 + len(sections) + 4
    header = b"GRIB" + bytes(2) + bytes([0, edition]) + struct.pack(">Q", total)
    return header + sections + b"7777"
