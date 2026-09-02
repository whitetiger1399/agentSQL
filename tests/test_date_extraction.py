from agent_sql.date_extraction import extract_relative_month_range


def test_extracts_ordinal_range_from_last_month():
    window = extract_relative_month_range(
        "Show me frames from Kranji Highway from the 15th to 18th of last month"
    )
    assert window is not None
    assert window.kind == "relative_month_range"
    assert window.month_offset == -1
    assert window.start_day == 15
    assert window.end_day == 18


def test_extracts_this_and_next_month_variants():
    assert extract_relative_month_range("1st through 3rd of this month").month_offset == 0
    assert extract_relative_month_range("2 until 4 of next month").month_offset == 1


def test_invalid_day_order_is_not_extracted():
    assert extract_relative_month_range("20th to 10th of last month") is None
