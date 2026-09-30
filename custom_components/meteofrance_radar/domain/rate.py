"""Rain rate from raw ACRR values, and the downgrade of a frame to class indices."""

from __future__ import annotations

from typing import Final

import numpy as np
from numpy.typing import NDArray

from .models import AcrrFrame, ClassFrame, Scaling
from .palette import LEVELS_MMH, classify

SLOTS_PER_HOUR: Final = 12


def acrr_rate(raw: NDArray[np.uint16], scaling: Scaling) -> NDArray[np.float32]:
    """Rain rate in mm/h of raw 5-minute accumulations, pointwise, any shape.

    rate = (raw * gain + offset) * 12. Undetect cells are dry (0.0), nodata cells are NaN.
    """
    rate = (raw.astype(np.float32) * np.float32(scaling.gain) + np.float32(scaling.offset)) * (
        np.float32(SLOTS_PER_HOUR)
    )
    rate[raw == scaling.undetect] = 0.0
    rate[raw == scaling.nodata] = np.nan
    return rate


def to_class_frame(frame: AcrrFrame) -> ClassFrame:
    """Downgrade a lossless frame to palette class indices on the same source grid."""
    return ClassFrame(
        slot=frame.slot,
        grid=frame.grid,
        levels_mmh=LEVELS_MMH,
        idx=classify(acrr_rate(frame.raw, frame.scaling)),
    )
