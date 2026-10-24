"""Retry with exponential backoff for transient failures."""

import time
from typing import Callable, TypeVar

T = TypeVar("T")

TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}


def is_transient(exc: BaseException) -> bool:
    """Rate limits, server errors, and network blips are worth retrying; client errors aren't."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code in TRANSIENT_STATUS
    return isinstance(exc, (ConnectionError, TimeoutError))


def retry(
    fn: Callable[[], T],
    attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    is_retryable: Callable[[BaseException], bool] = is_transient,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> T:
    """Call `fn`; on a retryable error wait base*2^n (capped) and try again, up to `attempts`."""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == attempts or not is_retryable(exc):
                raise
            delay = min(max_delay, base_delay * 2 ** (attempt - 1))
            if on_retry:
                on_retry(attempt, exc, delay)
            sleep(delay)
    raise AssertionError("unreachable")
