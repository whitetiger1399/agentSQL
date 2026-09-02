from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from rapidfuzz import fuzz

from .models import (
    DateKind,
    DateWindow,
    QueryPlan,
    RelativePeriod,
    ResolvedFilters,
    SessionContext,
)


SGT = ZoneInfo("Asia/Singapore")
UTC = timezone.utc
WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class ResolutionError(ValueError):
    def __init__(self, message: str, suggestions: list[str] | None = None):
        super().__init__(message)
        self.suggestions = suggestions or []


@dataclass(frozen=True)
class CameraCandidate:
    canonical: str
    terms: tuple[str, ...]


def _camera_candidates(cameras: list[dict[str, Any]]) -> list[CameraCandidate]:
    candidates: list[CameraCandidate] = []
    for camera in cameras:
        if camera.get("active") is False:
            continue
        canonical = str(camera.get("camera_name", "")).strip()
        if not canonical:
            continue
        terms = [canonical]
        acronym = str(camera.get("acronym", "")).strip()
        if acronym:
            terms.append(acronym)
        terms.extend(str(alias).strip() for alias in camera.get("aliases", []) if str(alias).strip())
        candidates.append(CameraCandidate(canonical, tuple(terms)))
    return candidates


def resolve_camera_terms(terms: list[str], cameras: list[dict[str, Any]]) -> list[str]:
    if not terms:
        return []
    candidates = _camera_candidates(cameras)
    if not candidates:
        raise ResolutionError("No active cameras are available.")

    resolved: list[str] = []
    for requested in terms:
        query = requested.strip().casefold()
        scored: list[tuple[float, str]] = []
        for candidate in candidates:
            score = max(fuzz.WRatio(query, term.casefold()) for term in candidate.terms)
            scored.append((float(score), candidate.canonical))
        scored.sort(reverse=True)
        best_score, best_name = scored[0]
        suggestions = [name for _, name in scored[:3]]
        if best_score < 72:
            raise ResolutionError(f"I could not confidently match camera ‘{requested}’.", suggestions)
        if len(scored) > 1 and best_score < 92 and best_score - scored[1][0] < 5:
            raise ResolutionError(f"Camera ‘{requested}’ is ambiguous.", suggestions)
        if best_name not in resolved:
            resolved.append(best_name)
    return resolved


def merge_context(plan: QueryPlan, context: SessionContext) -> tuple[QueryPlan, SessionContext]:
    base = SessionContext() if plan.reset_context else context
    data = plan.model_dump()
    if plan.inherit_cameras and not plan.camera_terms:
        data["camera_terms"] = list(base.camera_names)
    if plan.inherit_date and plan.date_window.kind == DateKind.NONE:
        data["date_window"] = base.date_window.model_dump()
        if not plan.weekdays:
            data["weekdays"] = list(base.weekdays)
    if plan.inherit_time:
        if plan.start_time is None:
            data["start_time"] = base.start_time
        if plan.end_time is None:
            data["end_time"] = base.end_time
    return QueryPlan.model_validate(data), base


def _date_bounds(window: DateWindow, now: datetime) -> tuple[date | None, date | None, str]:
    today = now.astimezone(SGT).date()
    if window.kind == DateKind.NONE:
        return None, None, "Any date"
    if window.kind == DateKind.EXACT:
        assert window.exact_date is not None
        return window.exact_date, window.exact_date, window.exact_date.isoformat()
    if window.kind == DateKind.RANGE:
        assert window.start_date is not None and window.end_date is not None
        return window.start_date, window.end_date, f"{window.start_date.isoformat()} to {window.end_date.isoformat()}"

    period = window.relative_period
    if period == RelativePeriod.TODAY:
        return today, today, "Today"
    if period == RelativePeriod.YESTERDAY:
        day = today - timedelta(days=1)
        return day, day, "Yesterday"
    if period == RelativePeriod.TOMORROW:
        day = today + timedelta(days=1)
        return day, day, "Tomorrow"
    if period == RelativePeriod.THIS_WEEK:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6), "This week"
    if period == RelativePeriod.LAST_WEEK:
        end = today - timedelta(days=today.weekday() + 1)
        return end - timedelta(days=6), end, "Last week"
    count = window.relative_count or 1
    if period == RelativePeriod.LAST_N_DAYS:
        return today - timedelta(days=count - 1), today, f"Last {count} days"
    if period == RelativePeriod.NEXT_N_DAYS:
        return today, today + timedelta(days=count - 1), f"Next {count} days"
    raise ResolutionError("The date window could not be resolved.")


def _local_interval(day: date, start: time | None, end: time | None) -> tuple[datetime, datetime]:
    start_time = start or time.min
    if end is None:
        end_day, end_time = day + timedelta(days=1), time.min
    elif start is not None and end <= start:
        end_day, end_time = day + timedelta(days=1), end
    else:
        end_day, end_time = day, end
    local_start = datetime.combine(day, start_time, tzinfo=SGT)
    local_end = datetime.combine(end_day, end_time, tzinfo=SGT)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def resolve_query_plan(
    plan: QueryPlan,
    cameras: list[dict[str, Any]],
    now: datetime | None = None,
) -> tuple[ResolvedFilters, SessionContext]:
    now = now or datetime.now(UTC)
    camera_names = resolve_camera_terms(plan.camera_terms, cameras)
    first, last, description = _date_bounds(plan.date_window, now)

    intervals: list[tuple[datetime, datetime]] = []
    if first is None and plan.weekdays:
        last = now.astimezone(SGT).date()
        first = last - timedelta(days=29)
        description = "Matching weekdays in the last 30 days"
    if first is not None and last is not None:
        day = first
        wanted = {WEEKDAY_INDEX[value] for value in plan.weekdays}
        while day <= last:
            if not wanted or day.weekday() in wanted:
                intervals.append(_local_interval(day, plan.start_time, plan.end_time))
            day += timedelta(days=1)
        if not intervals:
            raise ResolutionError("No requested weekdays occur in that date range.")
    elif plan.start_time is not None or plan.end_time is not None:
        raise ResolutionError("A time range needs a date or date range.")

    resolved = ResolvedFilters(
        camera_names=camera_names,
        intervals_utc=intervals,
        date_description=description,
    )
    updated = SessionContext(
        camera_names=camera_names,
        date_window=plan.date_window,
        weekdays=plan.weekdays,
        start_time=plan.start_time,
        end_time=plan.end_time,
    )
    return resolved, updated


def build_mongo_filter(filters: ResolvedFilters) -> dict[str, Any]:
    clauses: list[dict[str, Any]] = []
    if filters.camera_names:
        if len(filters.camera_names) == 1:
            clauses.append({"camera_name": filters.camera_names[0]})
        else:
            clauses.append({"camera_name": {"$in": filters.camera_names}})
    if filters.intervals_utc:
        date_clauses = [
            {"captured_at": {"$gte": start, "$lt": end}}
            for start, end in filters.intervals_utc
        ]
        clauses.append(date_clauses[0] if len(date_clauses) == 1 else {"$or": date_clauses})
    if not clauses:
        return {}
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}
