"""Typed error hierarchy shared by every layer of the integration.

No error ever holds the API key: messages carry URLs, statuses and slots only.
"""

from __future__ import annotations

from datetime import UTC, datetime

_SLOT_FORMAT = "%Y%m%dT%H%MZ"


class RadarError(Exception):
    """Base error carrying the slot and cause it relates to.

    Args:
        message: Human-readable description of the failure.
        slot: 5-minute UTC slot involved, if any.
        cause: Short description of the underlying cause, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        slot: datetime | None = None,
        cause: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.slot = slot
        self.cause = cause

    def __str__(self) -> str:
        parts = [self.message]
        if self.slot is not None:
            slot = self.slot.astimezone(UTC) if self.slot.tzinfo is not None else self.slot
            parts.append(f"slot={slot.strftime(_SLOT_FORMAT)}")
        if self.cause is not None:
            parts.append(f"cause={self.cause}")
        return " ".join(parts)


class ApiError(RadarError):
    """Failed call to the Météo-France API: network, non-2xx, bad JSON or no 500 m link.

    Args:
        status: HTTP status code, or None for a network-level failure.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        slot: datetime | None = None,
        cause: str | None = None,
    ) -> None:
        super().__init__(message, slot=slot, cause=cause)
        self.status = status

    def __str__(self) -> str:
        text = super().__str__()
        return text if self.status is None else f"{text} status={self.status}"


class ApiAuthError(ApiError):
    """The API refused the key (401 or 403)."""


class InvalidProductError(RadarError):
    """Unreadable HDF5 product, or wrong quantity, shape or dtype."""


class UnsupportedProjectionError(InvalidProductError):
    """The product projdef is one the numpy projection cannot handle."""


class GribFormatError(InvalidProductError):
    """A GRIB2 forecast field uses a layout the numpy reader does not support.

    Raised on a bad magic or edition, an unsupported grid or packing template, bits per
    value, bitmap or scanning mode, or a truncated message. The message names the field.
    """


class FrameFormatError(RadarError):
    """A stored frame file has a bad magic, version, header or codec."""


class SlotNotFoundError(RadarError):
    """No frame is stored for the requested slot."""


class StyleNotFoundError(RadarError):
    """The requested layer style is not the current one."""


class PeriodError(RadarError):
    """The requested period name is unknown."""


class StoragePathError(RadarError):
    """The storage path is not absolute or not writable."""
