"""Focused tests of the pure domain: grid, slots, palette, rate and the API key expiry."""

from __future__ import annotations

import base64
import json
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from custom_components.meteofrance_radar.api.apikey import api_key_expiry
from custom_components.meteofrance_radar.domain import palette
from custom_components.meteofrance_radar.domain.grid import FRANCE_GRID, TargetGrid
from custom_components.meteofrance_radar.domain.models import (
    AcrrFrame,
    Scaling,
    SourceGrid,
)
from custom_components.meteofrance_radar.domain.palette import (
    COLORS,
    LEVELS_MMH,
    NODATA_INDEX,
    classify,
    legend,
    palette_alpha,
    palette_rgb,
    style_id,
)
from custom_components.meteofrance_radar.domain.rate import acrr_rate, to_class_frame
from custom_components.meteofrance_radar.domain.slots import (
    ceil_slot,
    floor_slot,
    format_iso,
    format_slot,
    is_slot,
    parse_slot,
)

LATEST = datetime(2026, 9, 30, 10, 30, tzinfo=UTC)
SCALING = Scaling(gain=0.01, offset=0.0, nodata=65535.0, undetect=65534.0)
SOURCE = SourceGrid(
    projdef="+proj=stere +lat_0=90 +lon_0=0 +lat_ts=45 +ellps=WGS84",
    xsize=2,
    ysize=3,
    xscale=500.0,
    yscale=500.0,
    corners=(("UL", -9.9, 53.6), ("UR", 16.0, 53.6), ("LL", -6.0, 39.5), ("LR", 12.0, 39.5)),
)


def _jwt(claims: object) -> str:
    def part(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    return ".".join([part(b'{"alg":"HS256"}'), part(json.dumps(claims).encode()), "sig"])


@pytest.mark.parametrize(
    ("lon", "lat", "expected"),
    [
        (8.74, 41.93, (1335, 932)),  # Ajaccio
        (9.16, 41.39, (1360, 975)),  # Bonifacio
        (2.38, 51.03, (953, 136)),  # Dunkerque
    ],
)
def test_control_points_land_on_their_basemap_pixels(
    lon: float, lat: float, expected: tuple[int, int]
) -> None:
    col, row = FRANCE_GRID.lonlat_to_pixel(lon, lat)
    cols, rows = FRANCE_GRID.lonlat_to_pixel_arrays(np.array([lon]), np.array([lat]))

    assert abs(math.floor(col) - expected[0]) <= 1
    assert abs(math.floor(row) - expected[1]) <= 1
    assert (cols[0], rows[0]) == pytest.approx((col, row))
    assert FRANCE_GRID.contains_pixel(col, row)


def test_france_grid_parameters_bounds_and_pixel_centres() -> None:
    xs, ys = FRANCE_GRID.pixel_centers_3857()
    xmin, ymin, xmax, ymax = FRANCE_GRID.bounds_3857

    assert FRANCE_GRID.as_dict() == {
        "width": 1920,
        "height": 1080,
        "center_lon": 2.5,
        "center_lat": 46.6,
        "zoom": 6.4,
    }
    assert FRANCE_GRID.resolution == pytest.approx(1853.7, abs=0.05)
    assert xs.shape == ys.shape == (1080, 1920)
    assert xs[0, 0] == pytest.approx(xmin + FRANCE_GRID.resolution / 2)
    assert ys[-1, 0] == pytest.approx(ymin + FRANCE_GRID.resolution / 2)
    assert xs[0, -1] == pytest.approx(xmax - FRANCE_GRID.resolution / 2)
    assert ys[0, 0] == pytest.approx(ymax - FRANCE_GRID.resolution / 2)
    assert not FRANCE_GRID.contains_pixel(*FRANCE_GRID.lonlat_to_pixel(-60.0, 15.0))


def test_slot_parse_format_and_rounding() -> None:
    assert format_slot(LATEST) == "20260930T1030Z"
    assert format_iso(LATEST) == "2026-09-30T10:30:00Z"
    assert parse_slot("20260930T1030Z") == LATEST
    assert ceil_slot(datetime(2026, 9, 30, 10, 26, 1, tzinfo=UTC)) == LATEST
    assert ceil_slot(LATEST) == LATEST
    assert floor_slot(datetime(2026, 9, 30, 10, 34, 59, tzinfo=UTC)) == LATEST
    paris = LATEST.astimezone(datetime.fromisoformat("2026-09-30T12:30+02:00").tzinfo)
    assert format_slot(paris) == "20260930T1030Z"
    for bad in ("20260930T1031Z", "2026-09-30T10:30Z", ""):
        with pytest.raises(ValueError):
            parse_slot(bad)
    with pytest.raises(ValueError, match="naive"):
        is_slot(datetime(2026, 9, 30, 10, 30))


def test_classify_maps_nan_to_nodata_after_digitize() -> None:
    rate = np.array([np.nan, 0.0, 0.05, 0.1, 0.7, 69.9, 70.0, 500.0], dtype=np.float32)

    idx = classify(rate)

    assert idx.tolist() == [NODATA_INDEX, 0, 0, 1, 2, 10, 10, 10]
    assert idx.dtype == np.uint8


def test_palette_entries_and_legend_payload() -> None:
    assert len(palette_rgb()) == 36
    assert palette_rgb()[3:6] == [0xA2, 0x4B, 0xE8]
    assert palette_alpha() == bytes([0, *([217] * 10), 51])
    assert legend() == {
        "unit": "mm/h",
        "levels": [0.1, 0.5, 1, 2, 4, 6, 10, 16, 25, 40, 70],
        "colors": list(COLORS),
        "nodata_color": "#808080",
    }
    assert json.loads(json.dumps(legend())) == legend()


def test_style_id_changes_with_render_version_and_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    base = style_id(FRANCE_GRID)

    assert len(base) == 10
    assert style_id(FRANCE_GRID) == base
    other_grid = TargetGrid(width=1920, height=1080, center_lon=2.5, center_lat=46.6, zoom=6.5)
    assert style_id(other_grid) != base
    monkeypatch.setattr(palette, "RENDER_VERSION", palette.RENDER_VERSION + 1)
    assert style_id(FRANCE_GRID) != base


def test_acrr_rate_applies_gain_and_maps_undetect_and_nodata() -> None:
    raw = np.array([[0, 1, 50], [65534, 65535, 1000]], dtype=np.uint16)

    rate = acrr_rate(raw, SCALING)

    assert rate.dtype == np.float32
    assert rate.shape == raw.shape
    assert rate[0].tolist() == pytest.approx([0.0, 0.12, 6.0])
    assert rate[1, 0] == 0.0
    assert math.isnan(float(rate[1, 1]))
    assert float(rate[1, 2]) == pytest.approx(120.0)
    offset = acrr_rate(raw, Scaling(gain=0.5, offset=1.0, nodata=0.0, undetect=2.0))
    assert math.isnan(float(offset[0, 0]))
    assert float(offset[0, 1]) == pytest.approx(18.0)


def test_to_class_frame_classifies_on_the_source_grid() -> None:
    raw = np.array([[0, 1], [60, 65534], [65535, 1000]], dtype=np.uint16)
    frame = AcrrFrame(slot=LATEST, grid=SOURCE, scaling=SCALING, raw=raw)

    classes = to_class_frame(frame)

    assert classes.slot == LATEST
    assert classes.grid is SOURCE
    assert classes.levels_mmh == LEVELS_MMH
    assert classes.idx.dtype == np.uint8
    assert classes.idx.tolist() == [[0, 1], [6, 0], [NODATA_INDEX, 10]]
    assert SOURCE.corner("LL") == (-6.0, 39.5)
    with pytest.raises(KeyError):
        SOURCE.corner("XX")


def test_api_key_expiry_reads_the_jwt_exp_claim() -> None:
    expiry = datetime(2027, 9, 30, 12, 0, tzinfo=UTC)

    assert api_key_expiry(_jwt({"exp": int(expiry.timestamp())})) == expiry
    assert api_key_expiry(_jwt({"exp": expiry.timestamp() + 0.5})) == expiry + timedelta(
        milliseconds=500
    )
    assert api_key_expiry("plain-api-key-without-dots") is None
    assert api_key_expiry("a.%%%.c") is None
    assert api_key_expiry("a.bm90IGpzb24.c") is None
    assert api_key_expiry(_jwt(["exp", 1])) is None
    assert api_key_expiry(_jwt({"sub": "someone"})) is None
    assert api_key_expiry(_jwt({"exp": True})) is None
    assert api_key_expiry(_jwt({"exp": "1790000000"})) is None
    assert api_key_expiry(_jwt({"exp": 10**20})) is None
