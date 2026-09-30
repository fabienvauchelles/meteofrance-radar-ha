"""Minimal GRIB2 reader in numpy for the Météo-France forecast fields.

Only what the WCS APIs were measured to send is supported: one message holding one
field on a regular lat/lon grid (template 3.0) scanned west to east and north to
south, simple packing (template 5.0) with 0, 8, 16 or 32 bits per value, and no bitmap.
A tiny dry PIAF field comes with 0 bits: every value is the reference value R. Anything
else raises GribFormatError naming the field, so a format change on the Météo-France
side fails loudly instead of drawing wrong rain. Section 4 is not interpreted: the
request already fixes the parameter and the time.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from ..errors import GribFormatError

MAGIC: Final = b"GRIB"
END_MARKER: Final = b"7777"
EDITION: Final = 2
SECTION0_LENGTH: Final = 16
SECTION_HEADER_LENGTH: Final = 5
GRID_TEMPLATE_LATLON: Final = 0
PACKING_TEMPLATE_SIMPLE: Final = 0
SUPPORTED_BITS: Final = frozenset({0, 8, 16, 32})
NO_BITMAP: Final = 255
SCAN_WE_NS: Final = 0
MISSING_U32: Final = 0xFFFFFFFF
MICRO_DEGREES: Final = 1e6
FULL_CIRCLE_DEG: Final = 360.0
HALF_CIRCLE_DEG: Final = 180.0
_UNSIGNED_DTYPES: Final = {8: ">u1", 16: ">u2", 32: ">u4"}
_REQUIRED_SECTIONS: Final = (3, 5, 6, 7)
_SECTION3_LENGTH: Final = 72
_SECTION5_LENGTH: Final = 21
_SECTION6_LENGTH: Final = 6


@dataclass(frozen=True)
class LatLonGrid:
    """Regular lat/lon grid of point-registered cells, row 0 north.

    `lon0`, `lat0` are the centre of cell (row 0, col 0), lon in [-180, 180);
    `dlon`, `dlat` the positive spacing in degrees; `ni` columns and `nj` rows.
    """

    lon0: float
    lat0: float
    dlon: float
    dlat: float
    ni: int
    nj: int

    def key(self) -> str:
        """Stable text of every field, for table cache keys."""
        return f"latlon:{self.ni}x{self.nj}@{self.lon0!r},{self.lat0!r}d{self.dlon!r},{self.dlat!r}"


@dataclass(frozen=True)
class GribField:
    """Decoded field of shape (nj, ni), float32, in the unit of the product."""

    grid: LatLonGrid
    values: NDArray[np.float32]


def _sign_magnitude(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return -(value & (sign - 1)) if value & sign else value


def _sections(data: bytes) -> dict[int, bytes]:
    if data[:4] != MAGIC:
        raise GribFormatError("not a GRIB message", cause="magic")
    if len(data) < SECTION0_LENGTH:
        raise GribFormatError("GRIB message truncated", cause="section 0")
    if data[7] != EDITION:
        raise GribFormatError("unsupported GRIB edition", cause=f"edition={data[7]}")
    total = struct.unpack(">Q", data[8:16])[0]
    if total != len(data):
        raise GribFormatError(
            "GRIB total length disagrees with the data, one message expected",
            cause=f"total length={total} bytes={len(data)}",
        )
    sections: dict[int, bytes] = {}
    pos = SECTION0_LENGTH
    while data[pos : pos + 4] != END_MARKER:
        if pos + SECTION_HEADER_LENGTH > len(data):
            raise GribFormatError("GRIB message truncated", cause=f"section at byte {pos}")
        length, number = struct.unpack(">IB", data[pos : pos + SECTION_HEADER_LENGTH])
        if length < SECTION_HEADER_LENGTH or pos + length > len(data):
            raise GribFormatError("GRIB message truncated", cause=f"section {number}")
        if number in sections:
            raise GribFormatError("more than one field in the message", cause=f"section {number}")
        sections[number] = data[pos : pos + length]
        pos += length
    if pos + len(END_MARKER) != len(data):
        raise GribFormatError("data after the end marker", cause="7777")
    for number in _REQUIRED_SECTIONS:
        if number not in sections:
            raise GribFormatError("GRIB section missing", cause=f"section {number}")
    return sections


def _check_length(section: bytes, minimum: int, number: int) -> None:
    if len(section) < minimum:
        raise GribFormatError("GRIB section too short", cause=f"section {number}")


def _grid(section: bytes) -> LatLonGrid:
    _check_length(section, _SECTION3_LENGTH, 3)
    template = struct.unpack(">H", section[12:14])[0]
    if template != GRID_TEMPLATE_LATLON:
        raise GribFormatError("unsupported grid template", cause=f"template 3.{template}")
    points = struct.unpack(">I", section[6:10])[0]
    ni, nj, basic_angle = struct.unpack(">III", section[30:42])
    if basic_angle not in (0, MISSING_U32):
        raise GribFormatError("unsupported basic angle", cause=f"basic angle={basic_angle}")
    la1, lo1 = struct.unpack(">II", section[46:54])
    di, dj = struct.unpack(">II", section[63:71])
    scan = section[71]
    if scan != SCAN_WE_NS:
        raise GribFormatError("unsupported scanning mode", cause=f"scan mode={scan}")
    if ni == 0 or nj == 0 or points != ni * nj:
        raise GribFormatError("grid size disagrees", cause=f"points={points} ni={ni} nj={nj}")
    if MISSING_U32 in (di, dj) or di == 0 or dj == 0:
        raise GribFormatError("grid increments missing", cause=f"di={di} dj={dj}")
    lon0 = _sign_magnitude(lo1, 32) / MICRO_DEGREES
    if lon0 >= HALF_CIRCLE_DEG:
        lon0 -= FULL_CIRCLE_DEG
    return LatLonGrid(
        lon0=lon0,
        lat0=_sign_magnitude(la1, 32) / MICRO_DEGREES,
        dlon=di / MICRO_DEGREES,
        dlat=dj / MICRO_DEGREES,
        ni=ni,
        nj=nj,
    )


def _unpack(section5: bytes, section6: bytes, section7: bytes, count: int) -> NDArray[np.float32]:
    _check_length(section5, _SECTION5_LENGTH, 5)
    _check_length(section6, _SECTION6_LENGTH, 6)
    template = struct.unpack(">H", section5[9:11])[0]
    if template != PACKING_TEMPLATE_SIMPLE:
        raise GribFormatError("unsupported packing template", cause=f"template 5.{template}")
    # The bitmap comes first: with one, section 5 counts only the present values, and the
    # count check would hide the real reason.
    bitmap = section6[5]
    if bitmap != NO_BITMAP:
        raise GribFormatError("bitmaps are not supported", cause=f"bitmap indicator={bitmap}")
    packed_count = struct.unpack(">I", section5[5:9])[0]
    if packed_count != count:
        raise GribFormatError("packed value count disagrees", cause=f"values={packed_count}")
    reference = np.float32(struct.unpack(">f", section5[11:15])[0])
    binary_scale = _sign_magnitude(struct.unpack(">H", section5[15:17])[0], 16)
    decimal_scale = _sign_magnitude(struct.unpack(">H", section5[17:19])[0], 16)
    bits = section5[19]
    if bits not in SUPPORTED_BITS:
        raise GribFormatError("unsupported bits per value", cause=f"bits={bits}")
    divisor = np.float32(10.0**decimal_scale)
    if bits == 0:
        return np.full(count, reference / divisor, dtype=np.float32)
    payload = section7[SECTION_HEADER_LENGTH:]
    needed = count * bits // 8
    if len(payload) < needed:
        raise GribFormatError("GRIB data truncated", cause=f"section 7 {len(payload)} < {needed}")
    raw = np.frombuffer(payload, dtype=_UNSIGNED_DTYPES[bits], count=count).astype(np.float32)
    values = (reference + raw * np.float32(2.0**binary_scale)) / divisor
    return values.astype(np.float32)


def read_grib2(data: bytes) -> GribField:
    """Decode one GRIB2 message into a float32 field on its lat/lon grid.

    Raises:
        GribFormatError: bad magic or edition, not exactly one message, a template,
            packing, bit width, bitmap or scanning mode that is not supported, or a
            truncated message.
    """
    sections = _sections(data)
    grid = _grid(sections[3])
    count = grid.ni * grid.nj
    values = _unpack(sections[5], sections[6], sections[7], count)
    return GribField(grid=grid, values=values.reshape(grid.nj, grid.ni))
