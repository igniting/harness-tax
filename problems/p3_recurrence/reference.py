from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def expand(start_date, every_days, local_time, tz_name, count):
    tz = ZoneInfo(tz_name)
    y, m, d = map(int, start_date.split("-"))
    hh, mm = map(int, local_time.split(":"))
    base = datetime(y, m, d)
    out = []
    for k in range(count):
        day = base + timedelta(days=every_days * k)
        wall = datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz, fold=0)
        # detect nonexistent: round-trip through UTC changes the wall clock
        rt = wall.astimezone(timezone.utc).astimezone(tz)
        if rt.replace(tzinfo=None) != wall.replace(tzinfo=None):
            # gap: fold=0 maps into post-gap instant shifted forward by gap size
            resolved = rt
        else:
            # exists; ambiguous or unique -> fold=0 = earlier instant
            resolved = wall
        utc = resolved.astimezone(timezone.utc)
        out.append(utc.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return out
