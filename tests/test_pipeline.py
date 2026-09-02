from datetime import date, datetime, timezone

from agent_sql.models import DateWindow, QueryPlan, SessionContext
from agent_sql.pipeline import run_query


class FakePlanner:
    def __init__(self, plan):
        self.plan = plan
        self.called = False

    def extract_query_plan(self, message, context):
        self.called = True
        self.message = message
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
    planner = FakePlanner(QueryPlan(camera_terms=["PIE"]))
    result = run_query(
        "Show me frames from PIE lastest 5 frames",
        SessionContext(),
        planner,
        repo,
    )
    assert result.status == "ok"
    assert result.result_count == 5
    assert repo.limit == 5
    assert repo.sort_descending is True
    assert planner.message == "Show me frames from PIE latest 5 frames"
    assert result.message == "Found the latest 5 available frames for Pan Island Expressway."
    assert result.interpreted_filters["selection"] == "Latest 5 matching frames"
    assert result.interpreted_filters["date"] == "No date filter (searching all available dates)"
    assert [step.name for step in result.processing_steps] == [
        "1. Input normalization",
        "2. Pre-query safety checks",
        "3. Structured value extraction",
        "4. Conversation context merge",
        "5. Camera and date resolution",
        "6. Safe PyMongo query construction",
        "7. Read-only execution",
    ]


def test_fresh_date_query_does_not_inherit_or_copy_previous_camera():
    context = SessionContext(camera_names=["Pan Island Expressway"])
    copied_plan = QueryPlan(
        camera_terms=["Pan Island Expressway"],
        inherit_cameras=True,
        date_window=DateWindow(kind="exact", exact_date=date(2026, 7, 31)),
    )
    repo = FakeRepository()
    result = run_query(
        "Show me frames on July 31 2026",
        context,
        FakePlanner(copied_plan),
        repo,
        now=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )
    assert result.status == "ok"
    assert result.context.camera_names == []
    assert "all cameras" in result.message
    assert repo.filter == {
        "captured_at": {
            "$gte": datetime(2026, 7, 30, 16, tzinfo=timezone.utc),
            "$lt": datetime(2026, 7, 31, 16, tzinfo=timezone.utc),
        }
    }
