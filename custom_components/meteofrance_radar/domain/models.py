"""Value objects shared by the decoder, the frame store and the renderer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class SourceGrid:
    """Georeferencing of the source raster; corners are (name, lon, lat) cell edges, row 0 north."""

    projdef: str
    xsize: int
    ysize: int
    xscale: float
    yscale: float
    corners: tuple[tuple[str, float, float], ...]

    def corner(self, name: str) -> tuple[float, float]:
        """(lon, lat) of a corner among UL, UR, LL, LR.

        Raises:
            KeyError: unknown corner name.
        """
        for corner_name, lon, lat in self.corners:
            if corner_name == name:
                return lon, lat
        raise KeyError(name)

    def key(self) -> str:
        """Stable text of every field, for reprojection-table cache keys."""
        corners = ";".join(f"{name}:{lon!r},{lat!r}" for name, lon, lat in self.corners)
        return (
            f"{self.projdef.strip()}|{self.xsize}x{self.ysize}"
            f"|{self.xscale!r}x{self.yscale!r}|{corners}"
        )


@dataclass(frozen=True)
class Scaling:
    """Linear scaling of the raw ACRR values: value = raw * gain + offset, in mm per 5 min."""

    gain: float
    offset: float
    nodata: float
    undetect: float


@dataclass(frozen=True)
class AcrrFrame:
    """Lossless 5-minute accumulation of one slot, on the source grid."""

    slot: datetime
    grid: SourceGrid
    scaling: Scaling
    raw: NDArray[np.uint16]


@dataclass(frozen=True)
class ClassFrame:
    """Palette class indices of one slot on the source grid (downgraded, 3-hourly tier)."""

    slot: datetime
    grid: SourceGrid
    levels_mmh: tuple[float, ...]
    idx: NDArray[np.uint8]


type Frame = AcrrFrame | ClassFrame


class FrameKind(StrEnum):
    """Stored form of a frame."""

    ACRR_U16 = "acrr_u16"
    CLASS_U8 = "class_u8"


@dataclass(frozen=True)
class FrameEntry:
    """Index entry of a stored frame: its slot, stored form and file size in bytes."""

    slot: datetime
    kind: FrameKind
    size: int


@dataclass(frozen=True)
class ProductInfo:
    """Slot of a product and its deviations from the expected ODIM structure.

    An empty problems tuple means the product matches the expected structure.
    """

    slot: datetime
    problems: tuple[str, ...]
