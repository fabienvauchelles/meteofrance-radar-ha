"""Retry delays and the status bookkeeping every forecast job shares.

A refused key (401/403) is retried after an hour: a subscription does not appear by
itself. Any other failure is retried after 2, 4, 8, 16, then every 30 minutes. A status
change is logged once, never on every tick, and never with a URL query or a header.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from ..domain.forecast import ForecastProduct, ProductState, ProductStatus

_LOGGER = logging.getLogger(__name__)

ERROR_DELAYS: Final = tuple(timedelta(minutes=m) for m in (2, 4, 8, 16, 30))
FORBIDDEN_RETRY: Final = timedelta(hours=1)


def error_delay(failures: int) -> timedelta:
    """Wait before the next attempt after `failures` consecutive failures (1 or more)."""
    index = min(max(failures, 1), len(ERROR_DELAYS)) - 1
    return ERROR_DELAYS[index]


def describe_error(exc: BaseException) -> str:
    """Short error text for the state and diagnostics: type and message, no query string."""
    return f"{type(exc).__name__}: {exc}"


@dataclass
class ProductTracker:
    """Mutable status of one product; `state` is the frozen snapshot the service reports.

    Args:
        product: The product this tracker follows.
    """

    product: ForecastProduct
    status: ProductStatus = ProductStatus.PENDING
    run: datetime | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    next_check: datetime | None = None
    retry_at: datetime | None = None
    failures: int = 0

    @property
    def state(self) -> ProductState:
        """Frozen state of the product."""
        return ProductState(
            product=self.product,
            status=self.status,
            run=self.run,
            last_success=self.last_success,
            last_error=self.last_error,
            next_check=self.retry_at or self.next_check,
        )

    def due(self, now: datetime) -> bool:
        """False while a retry delay after a failure is running."""
        return self.retry_at is None or now >= self.retry_at

    def ok(self, now: datetime, run: datetime, next_check: datetime | None) -> None:
        """A run was fetched and saved."""
        self._set(ProductStatus.OK)
        self.run = run
        self.last_success = now
        self.last_error = None
        self.next_check = next_check
        self.retry_at = None
        self.failures = 0

    def waiting(self, next_check: datetime | None) -> None:
        """Nothing new yet: OK when a run is already saved, else PENDING."""
        self._set(ProductStatus.OK if self.run is not None else ProductStatus.PENDING)
        self.next_check = next_check
        self.retry_at = None

    def forbidden(self, now: datetime, exc: BaseException) -> None:
        """The key is not subscribed to this API: retry in an hour."""
        self.last_error = describe_error(exc)
        self.retry_at = now + FORBIDDEN_RETRY
        self.failures = 0
        self._set(ProductStatus.FORBIDDEN)

    def error(self, now: datetime, exc: BaseException) -> None:
        """Any other failure: retry after a growing delay."""
        self.failures += 1
        self.last_error = describe_error(exc)
        self.retry_at = now + error_delay(self.failures)
        self._set(ProductStatus.ERROR)
        _LOGGER.debug("%s failed %d times: %s", self.product, self.failures, self.last_error)

    def outside(self) -> None:
        """Home unset or outside the product domain: nothing to fetch."""
        self._set(ProductStatus.OUTSIDE)
        self.next_check = None
        self.retry_at = None
        self.failures = 0

    def _set(self, status: ProductStatus) -> None:
        if status is self.status:
            return
        previous, self.status = self.status, status
        if status in (ProductStatus.FORBIDDEN, ProductStatus.ERROR):
            _LOGGER.warning(
                "Forecast %s is now %s (was %s): %s",
                self.product,
                status,
                previous,
                self.last_error,
            )
        elif previous in (ProductStatus.FORBIDDEN, ProductStatus.ERROR):
            _LOGGER.info("Forecast %s is back to %s", self.product, status)
        else:
            _LOGGER.debug("Forecast %s is now %s", self.product, status)
