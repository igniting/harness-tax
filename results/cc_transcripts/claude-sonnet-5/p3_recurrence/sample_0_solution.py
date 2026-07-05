"""Expand a recurring local-time event into UTC occurrence timestamps."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def _resolve_local(dt_naive: datetime, tz: ZoneInfo) -> datetime:
    """Attach a timezone to a naive local datetime, handling gaps/ambiguity."""
    dt_fold0 = dt_naive.replace(tzinfo=tz, fold=0)
    dt_fold1 = dt_naive.replace(tzinfo=tz, fold=1)
    off0 = dt_fold0.utcoffset()
    off1 = dt_fold1.utcoffset()

    if off0 == off1:
        # Unambiguous: the wall time occurs exactly once.
        return dt_fold0

    if off0 > off1:
        # Ambiguous (fall-back overlap): use the earlier instant.
        return dt_fold0

    # Nonexistent (spring-forward gap): shift the wall clock forward by the
    # size of the gap and resolve using the post-transition offset.
    gap = off1 - off0
    shifted = dt_naive + gap
    return shifted.replace(tzinfo=tz, fold=1)


def expand(
    start_date: str, every_days: int, local_time: str, tz_name: str, count: int
) -> list[str]:
    year, month, day = (int(part) for part in start_date.split("-"))
    hour, minute = (int(part) for part in local_time.split(":"))
    base_date = date(year, month, day)
    tz = ZoneInfo(tz_name)

    occurrences = []
    for k in range(count):
        occ_date = base_date + timedelta(days=k * every_days)
        naive_dt = datetime(
            occ_date.year, occ_date.month, occ_date.day, hour, minute
        )
        local_dt = _resolve_local(naive_dt, tz)
        utc_dt = local_dt.astimezone(timezone.utc)
        occurrences.append(utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

    return occurrences
