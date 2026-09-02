from datetime import date, datetime, timezone

from agent_sql.models import DateWindow, QueryPlan, SessionContext
from agent_sql.pipeline import run_query


class FakePlanner:
    def __init__(self, plan):
        self.plan = plan
        self.called = False

    def extract_query_plan(self, message, context):
        self.called = True
        return self.plan


class FakeRepository:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.filter = None
        self.limit = None

    def camera_documents(self):
        return [{"camera_name": "Pan Island Expressway", "acronym": "PIE", "aliases": [], "active": True}]

    def find_traffic_frames(self, query_filter, limit=100, sort_descending=False):
        self.filter = query_filter
        self.limit = limit
        self.sort_descending = sort_descending
        return self.rows[:limit]


def test_pipeline_runs_valid_query_and_updates_context():
    plan = QueryPlan(
        camera_terms=["PIE"],
        date_window=DateWindow(kind="exact", exact_date=date(2026, 9, 1)),
    )
    repo = FakeRepository([{"frame_id": 1}])
    result = run_query(
        "PIE yesterday",
        SessionContext(),
        FakePlanner(plan),
        repo,
        now=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )
    assert result.status == "ok"
    assert result.result_count == 1
    assert result.context.camera_names == ["Pan Island Expressway"]
    assert repo.limit == 100


def test_guardrail_stops_before_planner_and_database():
    planner = FakePlanner(QueryPlan())
    repo = FakeRepository()
    result = run_query("Delete all frames", SessionContext(), planner, repo)
    assert result.status == "rejected"
    assert planner.called is False
    assert repo.filter is None


def test_model_rejection_does_not_query_database():
    repo = FakeRepository()
    result = run_query(
        "Tell me the weather",
        SessionContext(),
        FakePlanner(QueryPlan(intent="reject", rejection_reason="Only traffic frames are supported.")),
        repo,
    )
    assert result.status == "rejected"
    assert repo.filter is None


def test_latest_n_query_uses_requested_limit_and_descending_sort():
    repo = FakeRepository([{"frame_id": number} for number in range(20)])
    result = run_query(
        "Show me frames from CTE lastest 5 frames",
        SessionContext(),
        FakePlanner(QueryPlan(camera_terms=["PIE"])),
        repo,
    )
    assert result.status == "ok"
    assert result.result_count == 5
    assert repo.limit == 5
    assert repo.sort_descending is True
