import random
from bench_common.loader import load_solution

sol = load_solution()


class Oracle:
    """Literal spec implementation with lists (independent structure)."""
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError
        self.cap = capacity
        self.order = []           # LRU order, front = least recent
        self.data = {}            # key -> (value, expires_at)
        self.hits = 0
        self.misses = 0

    def _touch(self, key):
        if key in self.order:
            self.order.remove(key)
        self.order.append(key)

    def put(self, key, value, now, ttl):
        if key in self.data:
            self.data[key] = (value, now + ttl)
            self._touch(key)
            return
        if len(self.data) >= self.cap:
            for k in [k for k in self.order if self.data[k][1] <= now]:
                self.order.remove(k)
                del self.data[k]
            if len(self.data) >= self.cap:
                lru = self.order.pop(0)
                del self.data[lru]
        self.data[key] = (value, now + ttl)
        self._touch(key)

    def get(self, key, now):
        if key not in self.data:
            self.misses += 1
            return None
        value, exp = self.data[key]
        if now >= exp:
            del self.data[key]
            self.order.remove(key)
            self.misses += 1
            return None
        self.hits += 1
        self._touch(key)
        return value


def test_ttl_boundary_inclusive():
    c = sol.TTLCache(2)
    c.put("a", 1, now=0, ttl=10)
    assert c.get("a", now=9) == 1
    assert c.get("a", now=10) is None     # expired AT the instant
    assert c.stats() == (1, 1)
    assert len(c) == 0                     # expired-get deletes


def test_expired_get_is_miss_and_deletes():
    c = sol.TTLCache(2)
    c.put("a", 1, 0, 5)
    assert c.get("a", 7) is None
    assert c.stats() == (0, 1)
    assert len(c) == 0


def test_lru_eviction_order():
    c = sol.TTLCache(2)
    c.put("a", 1, 0, 100)
    c.put("b", 2, 1, 100)
    assert c.get("a", 2) == 1              # a now most-recent
    c.put("c", 3, 3, 100)                  # evicts b (LRU), not a
    assert c.get("b", 4) is None
    assert c.get("a", 4) == 1
    assert c.get("c", 4) == 3


def test_expired_evicted_before_lru():
    c = sol.TTLCache(2)
    c.put("a", 1, 0, 2)     # expires at 2
    c.put("b", 2, 0, 100)
    c.put("c", 3, 5, 100)   # a expired at t=5 -> purged; b survives
    assert c.get("b", 6) == 2
    assert c.get("c", 6) == 3
    assert c.get("a", 6) is None


def test_len_includes_expired_unpurged():
    c = sol.TTLCache(3)
    c.put("a", 1, 0, 1)
    c.put("b", 2, 0, 100)
    assert len(c) == 2      # a expired at t>=1 but not purged by anything yet


def test_overwrite_refreshes_and_touches():
    c = sol.TTLCache(2)
    c.put("a", 1, 0, 5)
    c.put("b", 2, 0, 100)
    c.put("a", 9, 1, 100)   # overwrite: a most-recent now
    c.put("c", 3, 2, 100)   # evicts b
    assert c.get("a", 3) == 9
    assert c.get("b", 3) is None
    assert c.stats() == (1, 1)


def test_put_never_changes_stats():
    c = sol.TTLCache(1)
    c.put("a", 1, 0, 10)
    c.put("b", 2, 0, 10)
    c.put("c", 3, 0, 10)
    assert c.stats() == (0, 0)


def test_differential_random_ops():
    rng = random.Random(552026)
    for trial in range(60):
        cap = rng.randint(1, 4)
        c, o = sol.TTLCache(cap), Oracle(cap)
        now = 0
        keys = ["k%d" % i for i in range(5)]
        for step in range(300):
            now += rng.randint(0, 3)
            k = rng.choice(keys)
            if rng.random() < 0.5:
                v, ttl = rng.randint(0, 99), rng.randint(1, 8)
                c.put(k, v, now, ttl)
                o.put(k, v, now, ttl)
            else:
                a, b = c.get(k, now), o.get(k, now)
                assert a == b, (trial, step, now, k, a, b)
            assert len(c) == len(o.data), (trial, step, now)
        assert c.stats() == (o.hits, o.misses), trial
