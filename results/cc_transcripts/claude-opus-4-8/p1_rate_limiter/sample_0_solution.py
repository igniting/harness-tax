"""Sliding-window rate limiter with per-key and global limits."""

from collections import deque


class RateLimiter:
    def __init__(self, global_limit: int, window_ms: int):
        self.global_limit = global_limit
        self.window_ms = window_ms
        # per-key config
        self._limit: dict[str, int] = {}
        self._weight: dict[str, int] = {}
        # per-key deque of (ts, weight) and running sum of weights
        self._events: dict[str, deque] = {}
        self._key_sum: dict[str, int] = {}
        # global deque of (ts, weight) and running sum
        self._global: deque = deque()
        self._global_sum = 0

    def set_key_limit(self, key: str, limit: int, weight: int = 1) -> None:
        self._limit[key] = limit
        self._weight[key] = weight
        if key not in self._events:
            self._events[key] = deque()
            self._key_sum[key] = 0

    def _evict_global(self, ts: int) -> None:
        cutoff = ts - self.window_ms  # events with t <= cutoff are expired
        g = self._global
        while g and g[0][0] <= cutoff:
            _, w = g.popleft()
            self._global_sum -= w

    def _evict_key(self, key: str, ts: int) -> None:
        cutoff = ts - self.window_ms
        dq = self._events[key]
        while dq and dq[0][0] <= cutoff:
            _, w = dq.popleft()
            self._key_sum[key] -= w

    def allow(self, key: str, ts: int) -> bool:
        if key not in self._limit:
            return False
        self._evict_global(ts)
        self._evict_key(key, ts)
        w = self._weight[key]
        if self._key_sum[key] + w > self._limit[key]:
            return False
        if self._global_sum + w > self.global_limit:
            return False
        self._events[key].append((ts, w))
        self._key_sum[key] += w
        self._global.append((ts, w))
        self._global_sum += w
        return True

    def usage(self, ts: int) -> dict[str, int]:
        result: dict[str, int] = {}
        for key in self._limit:
            self._evict_key(key, ts)
            result[key] = self._key_sum[key]
        return result
