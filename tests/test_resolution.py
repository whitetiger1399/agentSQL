from datetime import date, datetime, time, timezone

import pytest

from agent_sql.models import DateWindow, QueryPlan, ResolvedFilters, SessionContext
from agent_sql.resolution import (
    ResolutionError,
    build_mongo_filter,
    merge_context,
    resolve_camera_terms,
    resolve_query_plan,
)


CAMERAS = [
    {
        "camera_name": "Pan Island Expressway",
        "acronym": "PIE",
        "aliases": ["Pan Island"],
        "active": True,
    },
    {
        "camera_name": "Central Expressway",
        "acronym": "CTE",
        "aliases": ["Central Expy"],
        "active": True,
    },
]


@pytest.mark.parametrize("term", ["PIE", "Pan Island", "Pan Islan Expressway"])
def test_camera_name_alias_and_typo(term):
    assert resolve_camera_terms([term], CAMERAS) == ["Pan Island Expressway"]


def test_unknown_camera_returns_suggestions():
    with pytest.raises(ResolutionError) as error:
        resolve_camera_terms(["completely unknown road"], CAMERAS)
    assert error.value.suggestions


def test_singapore_date_converts_to_utc():
    plan = QueryPlan(
        camera_terms=["PIE"],
        date_window=DateWindow(kind="exact", exact_date=date(2026, 9, 2)),
        start_time=time(8),
        end_time=time(10),
    )
    resolved, _ = resolve_query_plan(
        plan, CAMERAS, now=datetime(2026, 9, 2, tzinfo=timezone.utc)
    )
    assert resolved.intervals_utc == [
        (
            datetime(2026, 9, 2, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 2, 2, tzinfo=timezone.utc),
        )
    ]


def test_overnight_window_rolls_into_next_day():
    plan = QueryPlan(
        date_window=DateWindow(kind="exact", exact_date=date(2026, 9, 2)),
        start_time=time(23),
        end_time=time(1),
    )
    resolved, _ = resolve_query_plan(plan, CAMERAS)
    start, end = resolved.intervals_utc[0]
    assert (end - start).total_seconds() == 2 * 60 * 60


def test_recurring_weekday_only_builds_matching_intervals():
    plan = QueryPlan(
        date_window=DateWindow(
            kind="range", start_date=date(2026, 8, 1), end_date=date(2026, 8, 10)
        ),
        weekdays=["monday"],
    )
    resolved, _ = resolve_query_plan(plan, CAMERAS)
    assert len(resolved.intervals_utc) == 2


def test_context_inheritance():
    context = SessionContext(
        camera_names=["Pan Island Expressway"],
        date_window=DateWindow(kind="exact", exact_date=date(2026, 9, 1)),
        start_time=time(8),
        end_time=time(10),
    )
    plan = QueryPlan(inherit_cameras=True, inherit_date=True, inherit_time=True)
    merged, _ = merge_context(plan, context)
    assert merged.camera_terms == ["Pan Island Expressway"]
    assert merged.date_window.exact_date == date(2026, 9, 1)
    assert merged.start_time == time(8)


def test_filter_uses_only_expected_shape():
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 9, 2, tzinfo=timezone.utc)
    result = build_mongo_filter(
        ResolvedFilters(camera_names=["Pan Island Expressway"], intervals_utc=[(start, end)])
    )
    assert result == {
        "$and": [
            {"camera_name": "Pan Island Expressway"},
            {"captured_at": {"$gte": start, "$lt": end}},
        ]
    }
