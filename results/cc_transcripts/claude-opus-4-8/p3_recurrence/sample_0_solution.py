"""Expand a recurring event into a list of UTC timestamps.

The single public function, :func:`expand`, takes the local calendar date of the
first occurrence, a recurrence stride in calendar days, an intended local
wall-clock time, an IANA timezone name, and a count, and returns each occurrence
converted to UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def _resolve_to_utc(local_date, hour, minute, tz):
    """Resolve one wall time on ``local_date`` in ``tz`` to a UTC datetime.

    Resolution rules:
      1. Existing, unambiguous wall time -> use it.
      2. Non-existent wall time (spring-forward gap) -> shift the wall clock
         forward by the size of the gap.
      3. Ambiguous wall time (fall-back overlap) -> use the earlier instant.
    """
    naive = datetime(local_date.year, local_date.month, local_date.day, hour, minute)

    # fold=0 gives the offset in effect *before* any transition at this wall time.
    # fold=1 gives the offset in effect *after* it.
    dt0 = naive.replace(tzinfo=tz, fold=0)
    dt1 = naive.replace(tzinfo=tz, fold=1)
    off0 = dt0.utcoffset()
    off1 = dt1.utcoffset()

    if off0 == off1:
        # Unique wall time (rule 1).
        chosen = dt0
    elif off0 < off1:
        # Spring-forward gap (rule 2): the offset jumps forward. Interpreting the
        # wall time with the pre-transition offset (fold=0) yields exactly the
        # instant whose post-transition wall clock is the original time shifted
        # forward by the gap size.
        chosen = dt0
    else:
        # Fall-back overlap (rule 3): fold=0 is the earlier of the two instants.
        chosen = dt0

    return chosen.astimezone(timezone.utc)


def expand(start_date: str, every_days: int, local_time: str, tz_name: str, count: int) -> list[str]:
    tz = ZoneInfo(tz_name)
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    hour, minute = (int(part) for part in local_time.split(":"))

    results: list[str] = []
    for k in range(count):
        local_date = start + timedelta(days=k * every_days)
        utc = _resolve_to_utc(local_date, hour, minute, tz)
        results.append(utc.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return results
