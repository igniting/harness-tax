from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def expand(start_date: str, every_days: int, local_time: str, tz_name: str, count: int) -> list[str]:
    year, month, day = map(int, start_date.split('-'))
    hour, minute = map(int, local_time.split(':'))
    tz = ZoneInfo(tz_name)
    base_date = datetime(year, month, day)
    delta = timedelta(days=every_days)
    utc = ZoneInfo('UTC')

    results = []
    for k in range(count):
        local_date = base_date + k * delta
        naive_dt = local_date.replace(hour=hour, minute=minute, second=0)
        local_dt = naive_dt.replace(tzinfo=tz, fold=0)
        utc_dt = local_dt.astimezone(utc)
        results.append(utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ'))

    return results
