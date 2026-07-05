Implement a Python module containing a class `RateLimiter` with this exact behavior.

`RateLimiter(global_limit: int, window_ms: int)` — a sliding-window rate limiter with
per-key limits and a global limit, using integer millisecond timestamps.

Methods:

1. `set_key_limit(key: str, limit: int, weight: int = 1) -> None`
   Registers (or re-registers) a key. `limit` is the max total *weight* admitted for
   that key within any sliding window of `window_ms`. `weight` is the cost charged
   per admitted request for that key. Re-registering updates limit/weight but keeps
   the key's admission history.

2. `allow(key: str, ts: int) -> bool`
   A request for `key` at time `ts`. Rules, applied in this order:
   a. If `key` was never registered via `set_key_limit`, return False (does not
      count against anything).
   b. Timestamps are non-decreasing across calls; you may rely on that.
   c. The relevant window is the half-open interval `(ts - window_ms, ts]`:
      an admitted event at exactly `ts - window_ms` has expired; one at
      `ts - window_ms + 1` has not.
   d. The request is admitted iff BOTH hold:
      - (per-key)  sum of weights of this key's admitted events in the window
                   + this request's current weight  <= the key's current limit
      - (global)   sum of weights of ALL admitted events in the window
                   + this request's current weight  <= global_limit
   e. If admitted, record the event with the key's *current* weight and return True.
      If rejected, record nothing and return False.

3. `usage(ts: int) -> dict[str, int]`
   Returns a dict mapping each registered key to the sum of weights of its admitted,
   unexpired events in the window `(ts - window_ms, ts]`. Keys with zero usage must
   still appear with value 0.

Notes:
- Rejected requests never consume quota.
- Weight changes via re-registration apply only to future requests; already-recorded
  events keep the weight they were recorded with.
- Aim for better than O(total history) per call; expired events should be evicted.

Return ONE complete Python module in a single ```python code block. No prose outside the block.
