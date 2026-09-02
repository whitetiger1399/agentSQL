from __future__ import annotations

import re


_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(insert|update|delete|drop|remove|replace|upsert|truncate|create\s+(?:a\s+)?(?:database|collection|index))\b",
            re.IGNORECASE,
        ),
        "I can only read traffic-camera data; write and schema-changing requests are not allowed.",
    ),
    (
        re.compile(
            r"\b(show|reveal|print|leak|expose)\b.{0,50}\b(prompt|secret|credential|api\s*key|connection\s*string|password)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "I cannot reveal prompts, secrets, credentials, or connection details.",
    ),
    (
        re.compile(
            r"\b(ignore|bypass|override|disregard)\b.{0,50}\b(instructions?|rules?|guardrails?|system|polic(?:y|ies))\b",
            re.IGNORECASE | re.DOTALL,
        ),
        "I cannot bypass or override the application's safety rules.",
    ),
    (
        re.compile(r"(?:\bdb\.|\baggregate\s*\(|\bmapreduce\b|\beval\s*\(|\$where\b|\bmongodb\s+command\b)", re.IGNORECASE),
        "Arbitrary MongoDB commands are not supported. Ask for traffic-camera frames in natural language.",
    ),
)


def obvious_rejection(message: str) -> str | None:
    normalized = message.strip()
    if not normalized:
        return "Please enter a traffic-camera question."
    if len(normalized) > 4_000:
        return "That request is too long. Please keep it under 4,000 characters."
    for pattern, reason in _RULES:
        if pattern.search(normalized):
            return reason
    return None
