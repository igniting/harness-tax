from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import random
from bench_common.loader import load_solution

sol = load_solution()


def oracle_one(date, hh, mm, tzname):
    """Independent brute-force resolution: scan UTC minute grid around the day."""
    tz = ZoneInfo(tzname)
    target = (date.year, date.month, date.day, hh, mm)
    # scan a generous UTC range covering the local date
    start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc) - timedelta(hours=30)
    matches = []
    t = start
    for _ in range(0, 90 * 60):  # 90 hours of minutes is overkill but safe
        loc = t.astimezone(tz)
        if (loc.year, loc.month, loc.day, loc.hour, loc.minute) == target:
            matches.append(t)
        t += timedelta(minutes=1)
    if matches:
        return min(matches)  # earlier instant for ambiguous, unique otherwise
    # nonexistent: shift forward by gap size = earliest instant whose local wall
    # time >= target on that date, i.e. first minute after the gap plus remainder
    # equivalent construction: fold=0 round trip
    wall = datetime(date.year, date.month, date.day, hh, mm, tzinfo=tz, fold=0)
    return wall.astimezone(timezone.utc)


def fmt(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_plain_days_ny():
    got = sol.expand("2026-01-05", 1, "09:00", "America/New_York", 3)
    assert got == ["2026-01-05T14:00:00Z", "2026-01-06T14:00:00Z", "2026-01-07T14:00:00Z"]


def test_spring_forward_gap_ny():
    # US DST 2026: spring forward Sun Mar 8, 02:00 -> 03:00 local
    got = sol.expand("2026-03-07", 1, "02:30", "America/New_York", 3)
    # Mar 7: 02:30 EST = 07:30Z ; Mar 8: gap -> 03:30 EDT = 07:30Z ; Mar 9: 02:30 EDT = 06:30Z
    assert got == ["2026-03-07T07:30:00Z", "2026-03-08T07:30:00Z", "2026-03-09T06:30:00Z"]


def test_fall_back_ambiguous_ny():
    # US DST 2026: fall back Sun Nov 1, 02:00 EDT -> 01:00 EST; 01:30 occurs twice
    got = sol.expand("2026-11-01", 1, "01:30", "America/New_York", 2)
    # earlier instant = EDT (-4): 01:30 EDT = 05:30Z ; next day unambiguous EST: 06:30Z
    assert got == ["2026-11-01T05:30:00Z", "2026-11-02T06:30:00Z"]


def test_calendar_day_arithmetic_not_86400s():
    # stepping across spring-forward with every_days must stay on wall-clock time
    got = sol.expand("2026-03-06", 2, "12:00", "America/New_York", 3)
    assert got == ["2026-03-06T17:00:00Z", "2026-03-08T16:00:00Z", "2026-03-10T16:00:00Z"]


def test_half_hour_zone_and_lord_howe():
    # Kolkata: no DST, +05:30 (Anshu's home zone; also a half-hour offset check)
    got = sol.expand("2026-07-04", 7, "18:15", "Asia/Kolkata", 2)
    assert got == ["2026-07-04T12:45:00Z", "2026-07-11T12:45:00Z"]
    # Lord Howe Island has a 30-minute DST shift
    got = sol.expand("2026-04-04", 1, "01:45", "Australia/Lord_Howe", 2)
    ref = [fmt(oracle_one(datetime(2026, 4, 4) + timedelta(days=k), 1, 45, "Australia/Lord_Howe")) for k in range(2)]
    assert got == ref


def test_differential_random_around_transitions():
    rng = random.Random(9)
    zones = ["America/New_York", "Europe/London", "Australia/Sydney", "America/Santiago"]
    # sample dates near each zone's 2026 transitions plus random dates
    seeds = [datetime(2026, 3, 7), datetime(2026, 3, 28), datetime(2026, 10, 24),
             datetime(2026, 4, 4), datetime(2026, 9, 5), datetime(2026, 11, 1)]
    cases = 0
    for tzname in zones:
        for seed in seeds:
            for _ in range(2):
                d0 = seed + timedelta(days=rng.randint(-1, 1))
                hh = rng.choice([0, 1, 2, 3, 23])
                mm = rng.choice([0, 15, 30, 59])
                n = rng.randint(1, 4)
                step = rng.randint(1, 3)
                got = sol.expand(d0.strftime("%Y-%m-%d"), step, f"{hh:02d}:{mm:02d}", tzname, n)
                want = [fmt(oracle_one(d0 + timedelta(days=step * k), hh, mm, tzname)) for k in range(n)]
                assert got == want, (tzname, d0, hh, mm, step, n, got, want)
                cases += 1
    assert cases >= 40
