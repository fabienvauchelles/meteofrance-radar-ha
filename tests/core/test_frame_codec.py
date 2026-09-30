"""The .mfr container on the real product: lossless round trips and every corruption rejected."""

from __future__ import annotations

import json
import lzma
import struct
from datetime import UTC, datetime

import numpy as np
import pytest

from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.domain.models import AcrrFrame, ClassFrame
from custom_components.meteofrance_radar.domain.palette import LEVELS_MMH, NODATA_INDEX
from custom_components.meteofrance_radar.domain.rate import to_class_frame
from custom_components.meteofrance_radar.errors import FrameFormatError
from custom_components.meteofrance_radar.store.frame_codec import (
    MAGIC,
    decode_frame,
    decode_header,
    encode_frame,
)
from tests.conftest import PRODUCT_FIXTURE

FIXTURE_SLOT = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)
PREFIX = struct.Struct("<4sBI")


@pytest.fixture(scope="module")
def acrr() -> AcrrFrame:
    return read_product(PRODUCT_FIXTURE.read_bytes())


@pytest.fixture(scope="module")
def acrr_file(acrr: AcrrFrame) -> bytes:
    return encode_frame(acrr)


@pytest.fixture(scope="module")
def class_frame(acrr: AcrrFrame) -> ClassFrame:
    return to_class_frame(acrr)


@pytest.fixture(scope="module")
def class_file(class_frame: ClassFrame) -> bytes:
    return encode_frame(class_frame)


def test_acrr_round_trip_is_lossless(acrr: AcrrFrame, acrr_file: bytes) -> None:
    decoded = decode_frame(acrr_file)

    assert isinstance(decoded, AcrrFrame)
    assert decoded.slot == FIXTURE_SLOT
    assert decoded.grid == acrr.grid
    assert decoded.scaling == acrr.scaling
    assert decoded.raw.dtype == np.uint16
    assert decoded.raw.shape == (3472, 3472)
    assert np.array_equal(decoded.raw, acrr.raw)
    assert len(acrr_file) < acrr.raw.nbytes // 20


def test_acrr_header_fields(acrr: AcrrFrame, acrr_file: bytes) -> None:
    header, start = decode_header(acrr_file)

    assert acrr_file[:4] == MAGIC
    assert acrr_file[4] == 1
    assert start == 9 + PREFIX.unpack_from(acrr_file)[2]
    assert header["slot"] == "20260930T1030Z"
    assert header["kind"] == "acrr_u16"
    assert header["codec"] == "xz"
    assert header["shuffle"] == 2
    assert header["shape"] == [3472, 3472]
    assert header["grid"]["projdef"] == acrr.grid.projdef
    assert [c[0] for c in header["grid"]["corners"]] == [c[0] for c in acrr.grid.corners]
    assert header["scaling"] == {
        "gain": 0.01,
        "offset": 0.0,
        "nodata": 65535.0,
        "undetect": 65534.0,
    }
    assert "classes" not in header
    assert list(header) == sorted(header)
    assert acrr_file[start : start + 6] == b"\xfd7zXZ\x00"


def test_class_round_trip_is_lossless(class_frame: ClassFrame, class_file: bytes) -> None:
    decoded = decode_frame(class_file)
    header, _ = decode_header(class_file)

    assert isinstance(decoded, ClassFrame)
    assert decoded.slot == FIXTURE_SLOT
    assert decoded.grid == class_frame.grid
    assert decoded.levels_mmh == tuple(float(v) for v in LEVELS_MMH)
    assert decoded.idx.dtype == np.uint8
    assert np.array_equal(decoded.idx, class_frame.idx)
    assert header["kind"] == "class_u8"
    assert header["codec"] == "xz"
    assert header["shuffle"] == 1
    assert header["classes"]["nodata_index"] == NODATA_INDEX
    assert "scaling" not in header


def _with_header(data: bytes, mutate: dict[str, object]) -> bytes:
    header, start = decode_header(data)
    header.update(mutate)
    body = json.dumps(header, sort_keys=True).encode()
    return PREFIX.pack(MAGIC, 1, len(body)) + body + data[start:]


def test_corrupted_files_raise_frame_format_error(class_file: bytes) -> None:
    _, start = decode_header(class_file)
    payload = class_file[start:]
    raw = lzma.decompress(payload)
    corruptions = {
        "magic": b"XXXX" + class_file[4:],
        "version": class_file[:4] + b"\x02" + class_file[5:],
        "header length past end": class_file[:5] + struct.pack("<I", 10**9) + class_file[9:],
        "header length off by one": class_file[:5]
        + struct.pack("<I", PREFIX.unpack_from(class_file)[2] - 1)
        + class_file[9:],
        "truncated prefix": class_file[:6],
        "codec": _with_header(class_file, {"codec": "zstd"}),
        "kind": _with_header(class_file, {"kind": "float32"}),
        "shape vs payload length": _with_header(class_file, {"shape": [3472, 3471]}),
        "flat shape": _with_header(class_file, {"shape": [3472 * 3472]}),
        "payload length": class_file[:start] + lzma.compress(raw[:-1]),
        "payload bytes": class_file[:start] + payload[: len(payload) // 2],
        "missing grid": _with_header(class_file, {"grid": None}),
    }
    for name, data in corruptions.items():
        try:
            decode_frame(data)
        except FrameFormatError:
            continue
        pytest.fail(f"corrupted {name} was accepted")
