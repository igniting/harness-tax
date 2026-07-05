from collections import deque


class RateLimiter:
    def __init__(self, global_limit: int, window_ms: int):
        self.global_limit = global_limit
        self.window_ms = window_ms
        self.keys = {}          # key -> (limit, weight)
        self.events = {}        # key -> deque[(ts, weight)]
        self.key_usage = {}     # key -> current in-window weight sum
        self.global_usage = 0
        self.global_events = deque()  # (ts, weight, key)

    def set_key_limit(self, key, limit, weight=1):
        self.keys[key] = (limit, weight)
        if key not in self.events:
            self.events[key] = deque()
            self.key_usage[key] = 0

    def _evict(self, ts):
        cutoff = ts - self.window_ms
        while self.global_events and self.global_events[0][0] < cutoff:
            ets, w, k = self.global_events.popleft()
            self.global_usage -= w
            # also evict from the per-key deque lazily below
        for k, dq in self.events.items():
            while dq and dq[0][0] < cutoff:
                _, w = dq.popleft()
                self.key_usage[k] -= w

    def allow(self, key, ts):
        if key not in self.keys:
            return False
        self._evict(ts)
        limit, weight = self.keys[key]
        if self.key_usage[key] + weight > limit:
            return False
        if self.global_usage + weight > self.global_limit:
            return False
        self.events[key].append((ts, weight))
        self.key_usage[key] += weight
        self.global_events.append((ts, weight, key))
        self.global_usage += weight
        return True

    def usage(self, ts):
        self._evict(ts)
        return {k: self.key_usage[k] for k in self.keys}
