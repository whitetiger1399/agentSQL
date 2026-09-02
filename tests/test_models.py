from datetime import date

import pytest
from pydantic import ValidationError

from agent_sql.models import DateKind, DateWindow, QueryPlan


def test_strict_plan_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        QueryPlan.model_validate({"intent": "query", "mongo_filter": {}})


def test_exact_date_requires_value():
    with pytest.raises(ValidationError):
        DateWindow(kind=DateKind.EXACT)


def test_range_must_be_ordered():
    with pytest.raises(ValidationError):
        DateWindow(kind=DateKind.RANGE, start_date=date(2026, 9, 2), end_date=date(2026, 9, 1))


def test_rejection_requires_reason():
    with pytest.raises(ValidationError):
        QueryPlan(intent="reject")
