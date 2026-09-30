"""Decoding of ODIM products: the real 10:30Z file, and every malformed shape rejected.

read_product is the adapter the collector calls on downloaded bytes; its structure
checks have no public-surface path of their own, so these are focused tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from custom_components.meteofrance_radar.decode.odim import read_product
from custom_components.meteofrance_radar.errors import (
    InvalidProductError,
    UnsupportedProjectionError,
)
from tests.support.odim_factory import (
    REAL_CORNERS,
    REAL_PROJDEF,
    SIZE,
    corrupt_bytes,
    dry_raw,
    write_odim,
)

REAL_H5 = Path(__file__).parents[1] / "fixtures" / "lame_d_eau_500_20260930T1030Z.h5"
SLOT = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)


def test_real_product_gives_slot_scaling_and_grid() -> None:
    frame = read_product(REAL_H5.read_bytes())

    assert frame.slot == SLOT
    assert frame.scaling.gain == pytest.approx(0.01)
    assert frame.scaling.offset == 0.0
    assert frame.scaling.nodata == 65535.0
    assert frame.scaling.undetect == 65534.0
    assert frame.raw.dtype == np.uint16
    assert frame.raw.shape == (SIZE, SIZE)
    grid = frame.grid
    assert grid.projdef == REAL_PROJDEF.strip()
    assert (grid.xsize, grid.ysize) == (SIZE, SIZE)
    assert (grid.xscale, grid.yscale) == (500.0, 500.0)
    assert grid.corner("UL") == REAL_CORNERS["UL"]
    assert [name for name, _, _ in grid.corners] == ["UL", "UR", "LL", "LR"]
    # The real product has rain, dry cells and no-data margins.
    assert int((frame.raw == 65535).sum()) > 0
    assert int(((frame.raw > 0) & (frame.raw < 65534)).sum()) > 0


def test_synthetic_product_keeps_values_and_ignores_quality() -> None:
    raw = dry_raw()
    raw[100, 200] = 1234
    with_quality = read_product(write_odim(slot=SLOT, raw=raw))
    without_quality = read_product(write_odim(slot=SLOT, raw=raw, omit_quality=True))

    assert np.array_equal(with_quality.raw, raw)
    assert np.array_equal(without_quality.raw, raw)
    assert with_quality.slot == SLOT


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"quantity": "DBZH"}, "quantity"),
        ({"raw": np.zeros((SIZE, SIZE - 1), dtype=np.uint16)}, "layout"),
        ({"raw": np.zeros((SIZE, SIZE), dtype=np.uint8)}, "layout"),
        ({"raw": np.zeros((SIZE, SIZE), dtype=np.float32)}, "layout"),
        ({"omit_slot": True}, "slot"),
        ({"slot": datetime(2026, 9, 30, 10, 32, tzinfo=UTC)}, "5-minute"),
    ],
    ids=["quantity", "shape", "dtype-u8", "dtype-f32", "no-slot", "off-grid-slot"],
)
def test_malformed_products_raise(kwargs: dict[str, object], match: str) -> None:
    params: dict[str, object] = {"slot": SLOT, **kwargs}
    data = write_odim(**params)  # type: ignore[arg-type]

    with pytest.raises(InvalidProductError, match=match):
        read_product(data)


@pytest.mark.parametrize("data", [corrupt_bytes(), b""], ids=["html", "empty"])
def test_non_hdf5_bytes_raise(data: bytes) -> None:
    with pytest.raises(InvalidProductError):
        read_product(data)


def test_truncated_product_raises() -> None:
    data = REAL_H5.read_bytes()

    with pytest.raises(InvalidProductError):
        read_product(data[: len(data) // 2])


def test_unsupported_projection_raises() -> None:
    data = write_odim(slot=SLOT, projdef="+proj=lcc +lat_1=45 +lat_2=50 +ellps=WGS84")

    with pytest.raises(UnsupportedProjectionError):
        read_product(data)
