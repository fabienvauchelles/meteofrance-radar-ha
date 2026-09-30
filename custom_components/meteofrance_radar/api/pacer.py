"""Request pacing for one forecast API: a sliding one-minute cap and a minimum spacing.

The forecast APIs allow 100 requests per minute each. A PIAF run needs 20 large
downloads in a row, so the pacer both spaces requests and keeps any rolling minute
under the cap, sleeping instead of letting the API answer 429.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Final

WINDOW_S: Final = 60.0


class RequestPacer:
    """Gate every request of one API through `wait()`.

    Args:
        max_per_minute: Most requests started in any rolling 60 seconds, at least 1.
        min_spacing_s: Least time between two request starts, in seconds, at least 0.
        monotonic: Clock in seconds, injectable for tests.
        sleep: Async sleep, injectable for tests.

    Raises:
        ValueError: a limit is out of range.
    """

    def __init__(
        self,
        *,
        max_per_minute: int,
        min_spacing_s: float,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if max_per_minute < 1:
            raise ValueError(f"max_per_minute must be at least 1, got {max_per_minute}")
        if min_spacing_s < 0:
            raise ValueError(f"min_spacing_s must not be negative, got {min_spacing_s}")
        self._max = max_per_minute
        self._spacing = min_spacing_s
        self._monotonic = monotonic
        self._sleep = sleep
        self._starts: deque[float] = deque()
        self._lock = asyncio.Lock()

    def _forget_old(self, now: float) -> None:
        while self._starts and self._starts[0] <= now - WINDOW_S:
            self._starts.popleft()

    def _delay(self, now: float) -> float:
        self._forget_old(now)
        delay = 0.0
        if self._starts:
            delay = self._starts[-1] + self._spacing - now
        if len(self._starts) >= self._max:
            delay = max(delay, self._starts[0] + WINDOW_S - now)
        return delay

    async def wait(self) -> None:
        """Wait until a request may start, then record its start."""
        async with self._lock:
            now = self._monotonic()
            delay = self._delay(now)
            while delay > 0:
                await self._sleep(delay)
                now = self._monotonic()
                delay = self._delay(now)
            self._starts.append(now)

    def requests_last_minute(self) -> int:
        """Requests started in the last 60 seconds."""
        self._forget_old(self._monotonic())
        return len(self._starts)
