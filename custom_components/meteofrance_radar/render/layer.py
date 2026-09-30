"""Frame to target-grid class indices, and to layer PNG bytes.

Values are gathered through the reprojection table before any arithmetic, so the
decoding rules only run on the 2 million target pixels, not the 12 million source
cells. Nearest-neighbour gather and the pointwise classification commute, which makes
a frame render identically before and after its downgrade to class indices. A
downgraded frame is read with the levels stored in its own file, mapped onto the
current classes, so a later palette change never misreads older history.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ..decode.reproject import ReprojectionTable
from ..domain.models import AcrrFrame, ClassFrame, Frame
from ..domain.palette import NODATA_INDEX, class_remap, classify
from ..domain.rate import acrr_rate
from ..errors import InvalidProductError
from .png import encode_layer_png


def _check_shape(frame: Frame, shape: tuple[int, ...]) -> None:
    expected = (frame.grid.ysize, frame.grid.xsize)
    if shape != expected:
        raise InvalidProductError(
            "frame data shape differs from its grid size",
            slot=frame.slot,
            cause=f"{shape} != {expected}",
        )


def _acrr_indices(frame: AcrrFrame, table: ReprojectionTable) -> NDArray[np.uint8]:
    _check_shape(frame, frame.raw.shape)
    raw = frame.raw[table.idx_r, table.idx_c]
    rate = acrr_rate(raw, frame.scaling)
    rate[~table.valid] = np.nan
    return classify(rate)


def _class_indices(frame: ClassFrame, table: ReprojectionTable) -> NDArray[np.uint8]:
    _check_shape(frame, frame.idx.shape)
    idx = class_remap(frame.levels_mmh)[frame.idx[table.idx_r, table.idx_c]]
    idx[~table.valid] = NODATA_INDEX
    return idx


def render_indices(frame: Frame, table: ReprojectionTable) -> NDArray[np.uint8]:
    """Palette indices of `frame` on the table's target grid; cells outside the source are 11.

    Raises:
        InvalidProductError: the frame data shape disagrees with its grid.
    """
    if isinstance(frame, AcrrFrame):
        return _acrr_indices(frame, table)
    return _class_indices(frame, table)


def render_layer(frame: Frame, table: ReprojectionTable) -> bytes:
    """Layer PNG bytes of `frame` on the table's target grid.

    Raises:
        InvalidProductError: the frame data shape disagrees with its grid.
    """
    return encode_layer_png(render_indices(frame, table))
