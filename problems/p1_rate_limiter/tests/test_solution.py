import random
from bench_common.loader import load_solution

sol = load_solution()


class Brute:
    """O(history) oracle implementing the spec literally."""
    def __init__(self, global_limit, window_ms):
        self.g, self.w = global_limit, window_ms
        self.keys = {}
        self.hist = []  # (ts, key, weight)

    def set_key_limit(self, key, limit, weight=1):
        self.keys[key] = (limit, weight)

    def _in_window(self, ts):
        return [(t, k, w) for (t, k, w) in self.hist if t > ts - self.w and t <= ts]

    def allow(self, key, ts):
        if key not in self.keys:
            return False
        limit, weight = self.keys[key]
        win = self._in_window(ts)
        key_sum = sum(w for (t, k, w) in win if k == key)
        glob_sum = sum(w for (_, _, w) in win)
        if key_sum + weight > limit or glob_sum + weight > self.g:
            return False
        self.hist.append((ts, key, weight))
        return True

    def usage(self, ts):
        win = self._in_window(ts)
        out = {k: 0 for k in self.keys}
        for (_, k, w) in win:
            out[k] += w
        return out


def test_boundary_semantics():
    rl = sol.RateLimiter(global_limit=10, window_ms=100)
    rl.set_key_limit("a", 1)
    assert rl.allow("a", 0) is True
    assert rl.allow("a", 100) is True    # (0,100]: event at 0 expired
    assert rl.allow("a", 199) is False   # (99,199]: event at 100 counts
    assert rl.allow("a", 201) is True    # (101,201]: expired


def test_unregistered_key():
    rl = sol.RateLimiter(5, 10)
    assert rl.allow("ghost", 1) is False
    rl.set_key_limit("a", 5)
    assert rl.allow("a", 1) is True


def test_global_limit_and_weights():
    rl = sol.RateLimiter(global_limit=5, window_ms=1000)
    rl.set_key_limit("a", 5, weight=2)
    rl.set_key_limit("b", 5, weight=2)
    assert rl.allow("a", 0) is True   # global 2
    assert rl.allow("b", 1) is True   # global 4
    assert rl.allow("a", 2) is False  # would be 6 > 5 (per-key a would be 4 <= 5)
    assert rl.usage(2) == {"a": 2, "b": 2}


def test_reregistration_keeps_history_old_weights():
    rl = sol.RateLimiter(100, 1000)
    rl.set_key_limit("a", 10, weight=3)
    assert rl.allow("a", 0) is True
    rl.set_key_limit("a", 10, weight=1)   # history kept, old event still weight 3
    assert rl.usage(1) == {"a": 3}
    assert rl.allow("a", 2) is True       # 3 + 1 <= 10
    assert rl.usage(3) == {"a": 4}


def test_rejected_requests_consume_nothing():
    rl = sol.RateLimiter(2, 100)
    rl.set_key_limit("a", 1)
    rl.set_key_limit("b", 2)
    assert rl.allow("a", 0) is True
    assert rl.allow("a", 1) is False
    assert rl.allow("a", 2) is False
    assert rl.allow("b", 3) is True   # global must be 2 (a:1,b:1), not inflated by rejections


def test_differential_random_streams():
    rng = random.Random(20260704)
    for trial in range(60):
        g = rng.randint(2, 12)
        w = rng.choice([10, 50, 100])
        rl, br = sol.RateLimiter(g, w), Brute(g, w)
        keys = ["k%d" % i for i in range(rng.randint(1, 4))]
        ts = 0
        for k in keys:
            lim = rng.randint(1, 8)
            wt = rng.randint(1, 3)
            rl.set_key_limit(k, lim, wt)
            br.set_key_limit(k, lim, wt)
        for step in range(200):
            ts += rng.randint(0, w // 3 + 1)
            op = rng.random()
            if op < 0.08:
                k = rng.choice(keys)
                lim, wt = rng.randint(1, 8), rng.randint(1, 3)
                rl.set_key_limit(k, lim, wt)
                br.set_key_limit(k, lim, wt)
            elif op < 0.92:
                k = rng.choice(keys + ["ghost"])
                a, b = rl.allow(k, ts), br.allow(k, ts)
                assert a == b, f"trial={trial} step={step} ts={ts} key={k}: got {a}, expected {b}"
            else:
                a, b = rl.usage(ts), br.usage(ts)
                assert a == b, f"trial={trial} step={step} ts={ts} usage: got {a}, expected {b}"
