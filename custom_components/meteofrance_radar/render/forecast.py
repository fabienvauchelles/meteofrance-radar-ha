"""Forecast rain-rate field to layer PNG, with the palette and encoding of the radar layers."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ..decode.reproject import ReprojectionTable
from ..domain.palette import classify
from ..errors import InvalidProductError
from .png import encode_layer_png


def render_field_layer(mm_h: NDArray[np.float32], table: ReprojectionTable) -> bytes:
    """Layer PNG of a mm/h field on the table's target grid; pixels outside the field are 11.

    Raises:
        InvalidProductError: the field is not 2-D or smaller than the table expects.
    """
    if mm_h.ndim != 2:
        raise InvalidProductError("forecast field is not 2-D", cause=f"shape={mm_h.shape}")
    rows, cols = mm_h.shape
    if table.valid.any() and (
        int(table.idx_r[table.valid].max()) >= rows or int(table.idx_c[table.valid].max()) >= cols
    ):
        raise InvalidProductError(
            "forecast field smaller than its reprojection table", cause=f"shape={mm_h.shape}"
        )
    rate = mm_h[table.idx_r, table.idx_c].astype(np.float32)
    rate[~table.valid] = np.nan
    return encode_layer_png(classify(rate))
