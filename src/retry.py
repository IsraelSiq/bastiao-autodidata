"""Bounded retry with exponential backoff for transient network failures."""

import time
from typing import Callable, TypeVar

import requests

T = TypeVar("T")


def is_transient(error: requests.RequestException) -> bool:
    """Retry connection problems, timeouts, 429 and 5xx; never other 4xx."""
    if isinstance(error, requests.HTTPError) and error.response is not None:
        status = error.response.status_code
        return status == 429 or status >= 500
    return True


def retry_transient(
    func: Callable[[], T],
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call func up to `attempts` times; re-raise the last error when exhausted."""
    attempts = max(1, attempts)
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except requests.RequestException as error:
            if attempt == attempts or not is_transient(error):
                raise
            sleep(min(max_delay, base_delay * 2 ** (attempt - 1)))
    raise AssertionError("unreachable")
