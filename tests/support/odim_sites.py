"""Radar sites listed in a real ODIM product, for the georeferencing tests only.

The integration never reads /how: the sites are an independent check that the
reprojection puts each radar on its own Web Mercator pixel.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import numpy as np

HOW_PATH = "/how"


@dataclass(frozen=True)
class RadarSite:
    """One radar of the composite, from /how/nodeN."""

    wmo: str
    name: str
    lat: float
    lon: float
    operating: bool


def _text(value: Any) -> str:
    if isinstance(value, bytes | np.bytes_):
        return bytes(value).decode("utf-8").strip("\x00")
    return str(value)


def _source_fields(source: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in source.split(","):
        key, sep, value = item.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def _site(name: str, node: Any) -> RadarSite:
    fields = _source_fields(_text(node["what"].attrs["source"]))
    return RadarSite(
        wmo=fields.get("WMO", ""),
        name=fields.get("PLC", fields.get("NOD", name)),
        lat=float(node["where"].attrs["lat"]),
        lon=float(node["where"].attrs["lon"]),
        # malfunc is the string 'True' or 'False', not a boolean.
        operating=_text(node["how"].attrs["malfunc"]) == "False",
    )


def read_radar_sites(path: Path) -> list[RadarSite]:
    """Radars listed in /how/nodeN, in node order; operating means malfunc == 'False'."""
    with h5py.File(path, "r") as handle:
        if HOW_PATH not in handle:
            return []
        how = handle[HOW_PATH]
        names = sorted(
            (name for name in how if name.startswith("node") and name[4:].isdigit()),
            key=lambda name: int(name[4:]),
        )
        return [_site(name, how[name]) for name in names]
