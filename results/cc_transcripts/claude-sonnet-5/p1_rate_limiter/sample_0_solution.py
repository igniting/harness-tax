from collections import deque


class RateLimiter:
    """Sliding-window rate limiter with per-key limits and a global limit."""

    def __init__(self, global_limit: int, window_ms: int) -> None:
        self.global_limit = global_limit
        self.window_ms = window_ms
        self._keys = {}  # key -> {"limit", "weight", "events": deque[(ts, weight)], "sum"}
        self._global_events = deque()  # (ts, weight)
        self._global_sum = 0

    def set_key_limit(self, key: str, limit: int, weight: int = 1) -> None:
        info = self._keys.get(key)
        if info is None:
            self._keys[key] = {"limit": limit, "weight": weight, "events": deque(), "sum": 0}
        else:
            info["limit"] = limit
            info["weight"] = weight

    def _evict_key(self, key: str, ts: int) -> None:
        info = self._keys[key]
        cutoff = ts - self.window_ms
        events = info["events"]
        while events and events[0][0] <= cutoff:
            _, w = events.popleft()
            info["sum"] -= w

    def _evict_global(self, ts: int) -> None:
        cutoff = ts - self.window_ms
        events = self._global_events
        while events and events[0][0] <= cutoff:
            _, w = events.popleft()
            self._global_sum -= w

    def allow(self, key: str, ts: int) -> bool:
        if key not in self._keys:
            return False

        self._evict_key(key, ts)
        self._evict_global(ts)

        info = self._keys[key]
        w = info["weight"]

        if info["sum"] + w <= info["limit"] and self._global_sum + w <= self.global_limit:
            info["events"].append((ts, w))
            info["sum"] += w
            self._global_events.append((ts, w))
            self._global_sum += w
            return True

        return False

    def usage(self, ts: int) -> dict:
        result = {}
        for key in self._keys:
            self._evict_key(key, ts)
            result[key] = self._keys[key]["sum"]
        return result
