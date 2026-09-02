from datetime import datetime, timezone

import pytest

from agent_sql.database import UnsafeQuery, _validate_filter, display_safe


def test_allowlisted_filter_is_accepted():
    _validate_filter(
        {
            "$and": [
                {"camera_name": {"$in": ["PIE"]}},
                {
                    "captured_at": {
                        "$gte": datetime(2026, 9, 1, tzinfo=timezone.utc),
                        "$lt": datetime(2026, 9, 2, tzinfo=timezone.utc),
                    }
                },
            ]
        }
    )


@pytest.mark.parametrize("query", [{"$where": "x"}, {"password": "x"}, {"captured_at": {"$gt": 1}}])
def test_unsafe_filters_are_rejected(query):
    with pytest.raises(UnsafeQuery):
        _validate_filter(query)


def test_datetimes_are_display_safe():
    result = display_safe({"captured_at": datetime(2026, 9, 1)})
    assert result["captured_at"].endswith("+00:00")
