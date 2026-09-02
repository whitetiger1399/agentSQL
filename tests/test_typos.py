from agent_sql.typos import normalize_query_text


def test_known_latest_typo_is_corrected():
    result = normalize_query_text("Show me the lastest 5 frames")
    assert result.text == "Show me the latest 5 frames"
    assert result.corrections == {"lastest": "latest"}


def test_high_confidence_domain_typo_is_corrected():
    assert normalize_query_text("frames yesterdai").text == "frames yesterday"


def test_camera_names_and_acronyms_are_not_modified():
    message = "Show CTE and Pan Islan Expressway frames"
    assert normalize_query_text(message).text == message


def test_short_and_ambiguous_words_are_not_modified():
    message = "Use PIE at noon"
    assert normalize_query_text(message).text == message
