"""API key expiry, read from the key's unverified JWT `exp` claim. The key is never logged."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Final

_JWT_PARTS: Final = 3


def api_key_expiry(key: str) -> datetime | None:
    """Expiry of a JWT-shaped key from its `exp` claim, without verifying the signature.

    Returns:
        The aware UTC expiry, or None when the key is not a JWT or carries no numeric `exp`.
    """
    parts = key.split(".")
    if len(parts) != _JWT_PARTS:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except binascii.Error, ValueError:
        return None
    exp = claims.get("exp") if isinstance(claims, dict) else None
    if isinstance(exp, bool) or not isinstance(exp, int | float):
        return None
    try:
        return datetime.fromtimestamp(exp, UTC)
    except OverflowError, OSError, ValueError:
        return None
