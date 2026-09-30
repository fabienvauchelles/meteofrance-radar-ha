"""Rain-rate classes, colours, no-data index, legend and layer style identifier."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Final

import numpy as np
from numpy.typing import NDArray

from .grid import TargetGrid

LEVELS_MMH: Final[tuple[float, ...]] = (0.1, 0.5, 1, 2, 4, 6, 10, 16, 25, 40, 70)
COLORS: Final[tuple[str, ...]] = (
    "#a24be8",
    "#6b5cf0",
    "#4a7df0",
    "#3fa9e0",
    "#46c9a8",
    "#7fdc5a",
    "#c8e84a",
    "#f5e03c",
    "#f5a031",
    "#e8452c",
)
RAIN_ALPHA: Final = 217
NODATA_INDEX: Final = 11
NODATA_RGB: Final[tuple[int, int, int]] = (128, 128, 128)
NODATA_COLOR: Final = "#808080"
NODATA_ALPHA: Final = 51
DRY_RGB: Final[tuple[int, int, int]] = (0, 0, 0)
TOP_CLASS: Final = len(COLORS)
STYLE_ID_LENGTH: Final = 10
INDEX_SPACE: Final = 256
LEGEND_UNIT: Final = "mm/h"
# Bump whenever decode, reprojection, classification or PNG encoding changes the pixels.
RENDER_VERSION = 1


def classify(rate: NDArray[np.float32]) -> NDArray[np.uint8]:
    """Map a rain rate in mm/h to palette indices.

    Index 0 is dry (< 0.1 mm/h), 1-10 the rain classes (>= 70 takes 10), 11 no data (NaN).
    The NaN mask is applied after digitize, which maps NaN past the last level.
    """
    idx = np.clip(np.digitize(rate, LEVELS_MMH), 0, TOP_CLASS).astype(np.uint8)
    idx[np.isnan(rate)] = NODATA_INDEX
    return idx


def class_remap(levels_mmh: Sequence[float]) -> NDArray[np.uint8]:
    """Lookup table from the indices of a frame classified with `levels_mmh` to current ones.

    A downgraded frame stores the levels it was classified with. Its class k (1 to
    len(levels_mmh) - 1) covers rates from levels_mmh[k - 1] up, so it takes the current
    class holding that lower bound. With the current levels the table is the identity.
    Dry stays 0; no data and any index outside the stored classes become NODATA_INDEX.
    """
    lut = np.full(INDEX_SPACE, NODATA_INDEX, dtype=np.uint8)
    lut[0] = 0
    classes = max(0, min(len(levels_mmh) - 1, NODATA_INDEX - 1))
    bounds = np.asarray(levels_mmh[:classes], dtype=np.float32)
    lut[1 : classes + 1] = classify(bounds)
    return lut


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def palette_rgb() -> list[int]:
    """Flat RGB palette of 12 entries (36 ints) for a Pillow mode "P" image."""
    entries = [DRY_RGB, *(_hex_to_rgb(color) for color in COLORS), NODATA_RGB]
    return [channel for rgb in entries for channel in rgb]


def palette_alpha() -> bytes:
    """Per-entry alpha (tRNS) for the 12 palette entries."""
    return bytes([0, *([RAIN_ALPHA] * len(COLORS)), NODATA_ALPHA])


def legend() -> dict[str, object]:
    """JSON-ready legend: class lower bounds in mm/h, their colours and the no-data colour.

    levels[i] is the lower bound of colors[i]; the last level is the upper bound of the last
    colour's class, which also takes everything above it.
    """
    return {
        "unit": LEGEND_UNIT,
        "levels": list(LEVELS_MMH),
        "colors": list(COLORS),
        "nodata_color": NODATA_COLOR,
    }


def style_id(grid: TargetGrid) -> str:
    """Short hash of everything that changes the layer pixels.

    Reads the module-level RENDER_VERSION at call time.
    """
    payload = {
        "levels": [float(level) for level in LEVELS_MMH],
        "colors": list(COLORS),
        "alpha": list(palette_alpha()),
        "nodata_rgb": list(NODATA_RGB),
        "grid": grid.key(),
        "render_version": RENDER_VERSION,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()[:STYLE_ID_LENGTH]
