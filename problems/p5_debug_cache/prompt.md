The following Python module implements `TTLCache`, an LRU cache with per-entry TTL
and hit/miss statistics, driven by an explicit clock. It contains BUGS. Fix the
module so it matches the specification below. Keep the public API identical
(`__init__(capacity)`, `put`, `get`, `stats`, `__len__`).

SPECIFICATION
- `put(key, value, now, ttl)`: insert/overwrite. Entry expires at `now + ttl`;
  it is CONSIDERED EXPIRED at any time `t >= now + ttl` (expiry instant inclusive).
  Overwriting an existing (even expired) key replaces value/expiry and makes the
  key most-recently-used. If inserting a NEW key while the cache is at capacity,
  first evict expired entries (any order); if still full, evict the
  LEAST-recently-used entry. `put` never changes hit/miss stats.
- `get(key, now)`: if key present and not expired -> return value, count a HIT,
  and mark key most-recently-used. If key absent -> return None, count a MISS.
  If key present but expired -> delete it, return None, count a MISS.
- Recency: both a successful `get` and any `put` of a key make it most recent.
  An expired-get does NOT (the entry is deleted).
- `stats()` -> `(hits, misses)`. `len(cache)` -> number of stored entries,
  INCLUDING expired-but-not-yet-purged ones.

BUGGY MODULE
```python
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._d = OrderedDict()   # key -> (value, expires_at)
        self._hits = 0
        self._misses = 0

    def put(self, key, value, now, ttl):
        if key in self._d:
            self._d[key] = (value, now + ttl)
            self._d.move_to_end(key, last=False)
            return
        if len(self._d) >= self.capacity:
            for k in list(self._d):
                _, exp = self._d[k]
                if exp > now:
                    del self._d[k]
            if len(self._d) >= self.capacity:
                self._d.popitem(last=True)
        self._d[key] = (value, now + ttl)

    def get(self, key, now):
        if key not in self._d:
            self._misses += 1
            return None
        value, expires_at = self._d[key]
        if now > expires_at:
            self._hits += 1
            return None
        self._hits += 1
        self._d.move_to_end(key)
        return value

    def stats(self):
        return (self._hits, self._misses)

    def __len__(self):
        return len(self._d)
```

Return the ENTIRE fixed module in a single ```python code block. No prose outside the block.
