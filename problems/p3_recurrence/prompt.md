Implement a Python module with a single function:

    expand(start_date: str, every_days: int, local_time: str, tz_name: str, count: int) -> list[str]

Expands a recurring event and returns its occurrences as UTC timestamps.

Inputs:
- start_date: "YYYY-MM-DD" — the LOCAL calendar date of the first occurrence.
- every_days: positive int — occurrence k (0-indexed) falls on the local calendar
  date start_date + k * every_days days. Date arithmetic is pure calendar-day
  arithmetic (no timezone involvement at this step).
- local_time: "HH:MM" (24h) — the intended LOCAL wall-clock time of each occurrence.
- tz_name: an IANA timezone name, e.g. "America/New_York". Use zoneinfo.
- count: number of occurrences to return.

Resolution rules for each occurrence's wall time on its local date:
1. If the wall time exists exactly once in that zone on that date, use it.
2. If the wall time does not exist (spring-forward gap), shift the wall clock
   FORWARD by the size of the gap (e.g. with a 1-hour gap, 02:30 becomes 03:30
   in the post-transition offset).
3. If the wall time is ambiguous (fall-back overlap), use the EARLIER of the two
   instants (the pre-transition offset).

Output: a list of `count` strings, each the occurrence converted to UTC and
formatted exactly as "YYYY-MM-DDTHH:MM:SSZ".

Return ONE complete Python module in a single ```python code block. No prose outside the block.
