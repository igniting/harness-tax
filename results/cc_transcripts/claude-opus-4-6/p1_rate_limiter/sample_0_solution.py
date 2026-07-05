from collections import deque


class RateLimiter:
    def __init__(self, global_limit: int, window_ms: int):
        self._global_limit = global_limit
        self._window_ms = window_ms
        self._keys: dict[str, tuple[int, int]] = {}
        self._key_events: dict[str, deque] = {}
        self._key_sum: dict[str, int] = {}
        self._global_events: deque = deque()
        self._global_sum: int = 0

    def set_key_limit(self, key: str, limit: int, weight: int = 1) -> None:
        self._keys[key] = (limit, weight)
        if key not in self._key_events:
            self._key_events[key] = deque()
            self._key_sum[key] = 0

    def _evict_key(self, key: str, ts: int) -> None:
        cutoff = ts - self._window_ms
        events = self._key_events[key]
        while events and events[0][0] <= cutoff:
            _, w = events.popleft()
            self._key_sum[key] -= w

    def _evict_global(self, ts: int) -> None:
        cutoff = ts - self._window_ms
        while self._global_events and self._global_events[0][0] <= cutoff:
            _, w = self._global_events.popleft()
            self._global_sum -= w

    def allow(self, key: str, ts: int) -> bool:
        if key not in self._keys:
            return False

        limit, weight = self._keys[key]

        self._evict_key(key, ts)
        self._evict_global(ts)

        if self._key_sum[key] + weight > limit:
            return False
        if self._global_sum + weight > self._global_limit:
            return False

        self._key_events[key].append((ts, weight))
        self._key_sum[key] += weight
        self._global_events.append((ts, weight))
        self._global_sum += weight
        return True

    def usage(self, ts: int) -> dict[str, int]:
        self._evict_global(ts)
        result = {}
        for key in self._keys:
            self._evict_key(key, ts)
            result[key] = self._key_sum[key]
        return result
