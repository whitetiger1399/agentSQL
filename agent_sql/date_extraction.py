from __future__ import annotations

import re

from .models import DateKind, DateWindow


_RELATIVE_MONTH_RANGE = re.compile(
    r"(?:from\s+(?:the\s+)?)?"
    r"(?P<start>\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(?:to|through|until)\s+(?:the\s+)?"
    r"(?P<end>\d{1,2})(?:st|nd|rd|th)?\s+of\s+"
    r"(?P<month>last|this|next)\s+month\b",
    re.IGNORECASE,
)

_MONTH_OFFSETS = {"last": -1, "this": 0, "next": 1}


def extract_relative_month_range(message: str) -> DateWindow | None:
    match = _RELATIVE_MONTH_RANGE.search(message)
    if not match:
        return None
    start_day = int(match.group("start"))
    end_day = int(match.group("end"))
    if not 1 <= start_day <= end_day <= 31:
        return None
    return DateWindow(
        kind=DateKind.RELATIVE_MONTH_RANGE,
        month_offset=_MONTH_OFFSETS[match.group("month").casefold()],
        start_day=start_day,
        end_day=end_day,
    )
