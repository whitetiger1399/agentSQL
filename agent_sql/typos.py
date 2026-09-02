from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process


# Intentionally narrow: unknown words and camera names must pass through untouched.
QUERY_KEYWORDS = frozenset(
    {
        "after",
        "before",
        "between",
        "camera",
        "cameras",
        "delete",
        "friday",
        "frame",
        "frames",
        "ignore",
        "insert",
        "latest",
        "monday",
        "records",
        "reveal",
        "rows",
        "saturday",
        "sunday",
        "thursday",
        "today",
        "tomorrow",
        "tuesday",
        "update",
        "wednesday",
        "weekday",
        "weekdays",
        "yesterday",
    }
)

EXPLICIT_CORRECTIONS = {
    "lastest": "latest",
    "lateset": "latest",
    "latset": "latest",
    "tommorow": "tomorrow",
    "tomorow": "tomorrow",
    "yesterdy": "yesterday",
}

_WORD = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class NormalizedQuery:
    text: str
    corrections: dict[str, str] = field(default_factory=dict)


def _correct_word(word: str) -> str:
    lowered = word.casefold()
    if lowered in QUERY_KEYWORDS:
        return word
    if lowered in EXPLICIT_CORRECTIONS:
        return EXPLICIT_CORRECTIONS[lowered]
    if len(lowered) < 5:
        return word

    matches = process.extract(lowered, QUERY_KEYWORDS, scorer=fuzz.ratio, limit=2)
    if not matches:
        return word
    best_word, best_score, _ = matches[0]
    runner_up = matches[1][1] if len(matches) > 1 else 0
    if best_score >= 86 and best_score - runner_up >= 8:
        return str(best_word)
    return word


def normalize_query_text(message: str) -> NormalizedQuery:
    corrections: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        original = match.group(0)
        corrected = _correct_word(original)
        if corrected.casefold() != original.casefold():
            corrections[original] = corrected
        return corrected

    return NormalizedQuery(text=_WORD.sub(replace, message), corrections=corrections)
