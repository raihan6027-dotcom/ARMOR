"""Small in-process sliding-window rate limiter (single-process demo deployment).

Consent-request limits are counted in the database instead (they must survive a
restart); this limiter guards the gateway per account, and per API key from
Fase 10e."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.core.exceptions import ArmorError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_s: float) -> None:
        """Record one hit for `key`; raise 429 if more than `limit` in `window_s`."""
        if limit <= 0:
            return
        stamp = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and stamp - hits[0] > window_s:
                hits.popleft()
            if len(hits) >= limit:
                retry = max(1, int(window_s - (stamp - hits[0])))
                raise ArmorError(
                    "RATE_LIMITED",
                    "Too many requests. Please wait a moment.",
                    429,
                    {"retry_after_s": retry},
                )
            hits.append(stamp)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()
