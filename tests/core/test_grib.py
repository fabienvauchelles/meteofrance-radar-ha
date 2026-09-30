"""GRIB2 reader on real Météo-France fields and on synthetic messages.

The decoder has no public-surface path of its own (the forecast jobs call it behind the
coordinator), so these are focused tests of pure logic.
"""

from __future__ import annotations

import lzma
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import ArrayLike

from custom_components.meteofrance_radar.decode.grib import read_grib2
from custom_components.meteofrance_radar.decode.latlon import latlon_cell
from custom_components.meteofrance_radar.errors import GribFormatError, InvalidProductError
from tests.support.grib_factory import write_grib2

FORECAST_DIR = Path(__file__).parents[1] / "fixtures" / "forecast"
PIAF_FULL = FORECAST_DIR / "piaf_20260930T1450Z_p030.grib2.xz"
PIAF_PIN = FORECAST_DIR / "piaf_pin_20260930T1450Z_1520Z.grib2"
AROMEPI_PIN = FORECAST_DIR / "aromepi_pin_20260930T1400Z_1800Z.grib2"
AROME_PIN = FORECAST_DIR / "arome_pin_20260930T1200Z_2100Z.grib2"
PIN_LON, PIN_LAT = 2.46, 48.80
# Values on the 2**-12 grid round-trip exactly.
FIELD = np.array([[0.0, 0.25, 1.5], [3.0, 0.0, 10.75]], dtype=np.float32)


def _grib(values: ArrayLike, **options: int) -> bytes:
    return write_grib2(values, lon0=2.0, lat0=49.0, dlon=0.01, dlat=0.01, **options)


def test_real_full_piaf_step_decodes_with_its_georeferencing() -> None:
    field = read_grib2(lzma.decompress(PIAF_FULL.read_bytes()))

    assert field.values.shape == (1051, 1651)
    assert field.values.dtype == np.float32
    assert field.grid.lon0 == -6.0
    assert field.grid.lat0 == 51.5
    assert field.grid.dlon == 0.01
    assert field.grid.dlat == 0.01
    assert float(field.values.max()) == pytest.approx(10.780029, abs=1e-6)
    peak = np.unravel_index(int(field.values.argmax()), field.values.shape)
    assert (int(peak[0]), int(peak[1])) == (345, 717)
    cell = latlon_cell(field.grid, PIN_LON, PIN_LAT)
    assert cell == (270, 846)
    assert float(field.values[cell]) == 0.0


def test_real_tiny_piaf_pin_is_a_zero_bit_constant_field() -> None:
    field = read_grib2(PIAF_PIN.read_bytes())

    assert field.values.shape == (3, 3)
    assert (field.grid.lon0, field.grid.lat0) == (2.45, 48.81)
    assert bool((field.values == 0.0).all())


@pytest.mark.parametrize(
    ("path", "centre"),
    [(AROMEPI_PIN, 0.4296875), (AROME_PIN, 0.17578125)],
)
def test_real_tiny_pins_give_the_centre_value(path: Path, centre: float) -> None:
    field = read_grib2(path.read_bytes())

    cell = latlon_cell(field.grid, PIN_LON, PIN_LAT)
    assert cell == (1, 1)
    assert float(field.values[cell]) == centre


@pytest.mark.parametrize("bits", [8, 16, 32])
def test_factory_round_trips_each_supported_width(bits: int) -> None:
    e = -12 if bits > 8 else -4
    values = FIELD if bits > 8 else np.array([[0, 1.5], [2, 15]], dtype=np.float32)
    data = _grib(values, e=e, bits=bits)

    field = read_grib2(data)

    np.testing.assert_array_equal(field.values, np.asarray(values, dtype=np.float32))
    assert (field.grid.ni, field.grid.nj) == np.asarray(values).shape[::-1]


def test_factory_round_trips_negative_longitude_and_constant_field() -> None:
    data = write_grib2(np.full((2, 4), 0.5), bits=0, lon0=-6.0, lat0=51.5, dlon=0.01, dlat=0.01)

    field = read_grib2(data)

    assert field.grid.lon0 == -6.0
    assert bool((field.values == 0.5).all())


@pytest.mark.parametrize(
    ("options", "field_name"),
    [
        ({"edition": 1}, "edition"),
        ({"template3": 1}, "template 3.1"),
        ({"template5": 3}, "template 5.3"),
        ({"bits": 12, "e": -4}, "bits=12"),
        ({"bitmap": 0}, "bitmap indicator=0"),
        ({"scan": 64}, "scan mode=64"),
        ({"truncate_data": 2}, "section 7"),
    ],
)
def test_unsupported_layouts_are_refused_naming_the_field(
    options: dict[str, int], field_name: str
) -> None:
    data = _grib(FIELD, **options)

    with pytest.raises(GribFormatError) as info:
        read_grib2(data)

    assert field_name in str(info.value)
    assert isinstance(info.value, InvalidProductError)


def test_bitmap_is_named_when_section_5_counts_only_present_values() -> None:
    # A real bitmapped field (full-domain AROME-PI) packs fewer values than grid points.
    data = bytearray(_grib(FIELD, bitmap=0))
    pos = 16
    while data[pos + 4] != 5:
        pos += int.from_bytes(data[pos : pos + 4], "big")
    data[pos + 5 : pos + 9] = (FIELD.size - 1).to_bytes(4, "big")

    with pytest.raises(GribFormatError) as info:
        read_grib2(bytes(data))

    assert "bitmap indicator=0" in str(info.value)


@pytest.mark.parametrize(
    "data",
    [b"<xml/>", b"GRIB", _grib(FIELD)[:-10], _grib(FIELD) * 2],
)
def test_not_grib_truncated_or_several_messages_are_refused(data: bytes) -> None:
    with pytest.raises(GribFormatError):
        read_grib2(data)
