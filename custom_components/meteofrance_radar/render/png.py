"""Indexed PNG encoding of a classified layer."""

from __future__ import annotations

import io

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from ..domain.palette import palette_alpha, palette_rgb


def encode_layer_png(idx: NDArray[np.uint8]) -> bytes:
    """Encode palette indices of shape (height, width) as a mode "P" PNG with tRNS alpha."""
    height, width = idx.shape
    pixels = np.ascontiguousarray(idx, dtype=np.uint8).tobytes()
    image = Image.frombytes("P", (width, height), pixels)
    image.putpalette(palette_rgb())
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", transparency=palette_alpha(), optimize=True)
    return buffer.getvalue()
