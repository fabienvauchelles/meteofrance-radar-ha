"""Synthetic ODIM_H5 lame d'eau files mirroring the real Météo-France 500 m structure.

Georeferencing helpers here use pyproj directly and never the integration's numpy
projection, so tests built on them stay independent of the code under test.
"""

from __future__ import annotations

import io
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray
from pyproj import Transformer

SIZE = 3472
CELL_M = 500.0
RAW_NODATA = 65535
RAW_UNDETECT = 65534
QUALITY_NODATA = 255
QUALITY_UNDETECT = 254
DEFAULT_QUALITY = 90
COVERAGE_RADIUS_CELLS = 1500
DATA_CHUNKS = (150, SIZE)
QUALITY_CHUNKS = (289, SIZE)
REAL_PROJDEF = (
    "+proj=stere +lat_0=90 +lon_0=0 +lat_ts=45 +ellps=WGS84 "
    "+x_0=619652.07 +y_0=5262818.34 +datum=WGS84 "
)
# Corner (lon, lat) copied from the real 10:30Z file.
REAL_CORNERS: dict[str, tuple[float, float]] = {
    "UL": (-9.965, 53.67),
    "UR": (17.564202528305234, 52.54813781717718),
    "LL": (-6.715173408021557, 38.14493289858148),
    "LR": (11.976054526221487, 37.45745953865351),
}


@dataclass(frozen=True)
class RadarSiteSpec:
    """One radar node to write under /how/nodeN."""

    wmo: str
    name: str
    lat: float
    lon: float
    operating: bool = True
    height: float = 100.0


@cache
def _to_projection() -> Transformer:
    return Transformer.from_crs("EPSG:4326", REAL_PROJDEF, always_xy=True)


@cache
def _upper_left_xy() -> tuple[float, float]:
    lon, lat = REAL_CORNERS["UL"]
    x, y = _to_projection().transform(lon, lat)
    return float(x), float(y)


def source_cell(lon: float, lat: float) -> tuple[int, int]:
    """(row, col) of the source cell containing a WGS84 point; row 0 is north."""
    x, y = _to_projection().transform(lon, lat)
    x_ul, y_ul = _upper_left_xy()
    return math.floor((y_ul - float(y)) / CELL_M), math.floor((float(x) - x_ul) / CELL_M)


@cache
def _coverage_mask() -> NDArray[np.bool_]:
    rows, cols = np.ogrid[:SIZE, :SIZE]
    centre = (SIZE - 1) / 2
    inside: NDArray[np.bool_] = (rows - centre) ** 2 + (cols - centre) ** 2 <= (
        COVERAGE_RADIUS_CELLS**2
    )
    inside.flags.writeable = False
    return inside


@cache
def _base_raw() -> NDArray[np.uint16]:
    raw = np.where(_coverage_mask(), np.uint16(0), np.uint16(RAW_NODATA)).astype(np.uint16)
    raw.flags.writeable = False
    return raw


@cache
def _base_quality() -> NDArray[np.uint8]:
    quality = np.where(_coverage_mask(), np.uint8(DEFAULT_QUALITY), np.uint8(QUALITY_NODATA))
    quality = quality.astype(np.uint8)
    quality.flags.writeable = False
    return quality


def dry_raw() -> NDArray[np.uint16]:
    """Writable copy of the default raw array: 0 inside a centred disc, 65535 outside."""
    return _base_raw().copy()


def with_peak(
    raw: NDArray[np.uint16], lon: float, lat: float, value: int, half: int = 4
) -> NDArray[np.uint16]:
    """Copy of raw with a (2*half+1)^2 block of value centred on the cell of (lon, lat)."""
    row, col = source_cell(lon, lat)
    result = raw.copy()
    result[max(row - half, 0) : row + half + 1, max(col - half, 0) : col + half + 1] = value
    return result


def corrupt_bytes() -> bytes:
    """Bytes that are not an HDF5 file."""
    return b"<html>gateway error</html>" * 64


def _text(value: str) -> np.bytes_:
    return np.bytes_(value.encode())


def _write_root(handle: h5py.File, slot: datetime, omit_slot: bool, projdef: str) -> None:
    handle.attrs["Conventions"] = _text("ODIM_H5/V2_3")
    what = handle.create_group("what")
    what.attrs["date"] = _text(slot.strftime("%Y%m%d"))
    what.attrs["object"] = _text("COMP")
    what.attrs["source"] = _text("CMT:ACRR_composite_metropole500_OPER,CTY:614,ORG:085")
    what.attrs["time"] = _text(slot.strftime("%H%M%S"))
    what.attrs["version"] = _text("H5rad 2.3")
    where = handle.create_group("where")
    for name, (lon, lat) in REAL_CORNERS.items():
        where.attrs[f"{name}_lat"] = np.float64(lat)
        where.attrs[f"{name}_lon"] = np.float64(lon)
    where.attrs["projdef"] = _text(projdef)
    where.attrs["xscale"] = np.float64(CELL_M)
    where.attrs["xsize"] = np.int64(SIZE)
    where.attrs["yscale"] = np.float64(CELL_M)
    where.attrs["ysize"] = np.int64(SIZE)
    dataset_what = handle.create_group("dataset1/what")
    start = slot - timedelta(minutes=5)
    dataset_what.attrs["product"] = _text("COMP")
    dataset_what.attrs["startdate"] = _text(start.strftime("%Y%m%d"))
    dataset_what.attrs["starttime"] = _text(start.strftime("%H%M%S"))
    if not omit_slot:
        dataset_what.attrs["enddate"] = _text(slot.strftime("%Y%m%d"))
        dataset_what.attrs["endtime"] = _text(slot.strftime("%H%M%S"))


def _write_image(
    handle: h5py.File, path: str, array: NDArray[np.generic], chunks: tuple[int, int]
) -> None:
    fitted = (min(chunks[0], array.shape[0]), min(chunks[1], array.shape[1]))
    dataset = handle.create_dataset(
        path, data=array, chunks=fitted, compression="gzip", compression_opts=6
    )
    dataset.attrs["CLASS"] = _text("IMAGE")
    dataset.attrs["IMAGE_VERSION"] = _text("1.2")


def _write_what(
    handle: h5py.File, path: str, quantity: str, nodata: float, undetect: float
) -> None:
    what = handle.create_group(path)
    what.attrs["gain"] = np.float64(0.01)
    what.attrs["nodata"] = np.float64(nodata)
    what.attrs["offset"] = np.float64(0.0)
    what.attrs["quantity"] = _text(quantity)
    what.attrs["undetect"] = np.float64(undetect)


def _write_sites(handle: h5py.File, slot: datetime, sites: Sequence[RadarSiteSpec]) -> None:
    how = handle.create_group("how")
    how.attrs["missing_nodes"] = _text(",".join(f"WMO:{s.wmo}" for s in sites if not s.operating))
    how.attrs["nodes"] = _text(",".join(f"WMO:{s.wmo}" for s in sites if s.operating))
    how.attrs["software"] = _text("SERVAL")
    how.attrs["sw_version"] = _text("3.2.2")
    for number, site in enumerate(sites, start=1):
        node = how.create_group(f"node{number}")
        node_how = node.create_group("how")
        node_how.attrs["malfunc"] = _text("False" if site.operating else "True")
        node_how.attrs["poltype"] = _text("simultaneous-dual")
        node_what = node.create_group("what")
        node_what.attrs["source"] = _text(
            f"CMT:OPERATIONNAL,NOD:fr{number:03d},PLC:{site.name},WMO:{site.wmo}"
        )
        if site.operating:
            node_what.attrs["date"] = _text(slot.strftime("%Y%m%d"))
            node_what.attrs["time"] = _text(slot.strftime("%H%M%S"))
        node_where = node.create_group("where")
        node_where.attrs["height"] = np.float64(site.height)
        node_where.attrs["lat"] = np.float64(site.lat)
        node_where.attrs["lon"] = np.float64(site.lon)


def write_odim(
    path: Path | None = None,
    *,
    slot: datetime,
    raw: NDArray[np.generic] | None = None,
    quality: NDArray[np.uint8] | None = None,
    quantity: str = "ACRR",
    projdef: str = REAL_PROJDEF,
    omit_slot: bool = False,
    omit_quality: bool = False,
    sites: Sequence[RadarSiteSpec] = (),
) -> bytes:
    """Build a synthetic 500 m lame d'eau file; also write it to path when given.

    Args:
        path: Optional destination file (parent directories are created).
        slot: End of the 5-minute accumulation (aware UTC).
        raw: Data array; default uint16 dry inside a centred disc, 65535 outside. Any
            dtype or shape is written as given, to build malformed products.
        quality: uint8 QIND; default 90 inside the disc, 255 outside.
        quantity: Value of /dataset1/data1/what quantity.
        projdef: Value of /where projdef.
        omit_slot: Leave out /dataset1/what enddate and endtime.
        omit_quality: Leave out the quality1 group.
        sites: Radar nodes written under /how/nodeN.

    Returns:
        The HDF5 file content.
    """
    slot = slot.astimezone(UTC)
    buffer = io.BytesIO()
    with h5py.File(buffer, "w") as handle:
        _write_root(handle, slot, omit_slot, projdef)
        data = _base_raw() if raw is None else raw
        _write_image(handle, "dataset1/data1/data", data, DATA_CHUNKS)
        _write_what(handle, "dataset1/data1/what", quantity, RAW_NODATA, RAW_UNDETECT)
        if not omit_quality:
            qind = _base_quality() if quality is None else quality
            _write_image(handle, "dataset1/data1/quality1/data", qind, QUALITY_CHUNKS)
            _write_what(
                handle, "dataset1/data1/quality1/what", "QIND", QUALITY_NODATA, QUALITY_UNDETECT
            )
        _write_sites(handle, slot, sites)
    content = buffer.getvalue()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return content
