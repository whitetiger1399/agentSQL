# Project Context

## Query pipeline

1. Receive user message.
2. Check scope and obvious prompt injection.
3. Extract a structured query plan using the LLM.
4. Validate the plan using Pydantic.
5. Resolve camera aliases and typos.
6. Resolve dates in Asia/Singapore.
7. Merge relevant conversational context.
8. Construct an allowlisted PyMongo query.
9. Execute a read-only query with a result limit.
10. Display frame metadata and interpreted filters.

## Synthetic data window

- `traffic_frames` contains synthetic hourly data from 1 August through
  30 September 2026 (14,640 records across 10 cameras).
- Future-dated rows exist only to keep relative-date testing useful throughout
  September—for example, asking for “yesterday” on 25 September.
- The session date is fixed when the app loads in `Asia/Singapore`.
- An explicit request after the session date is rejected as a future-frame query.
- A query with no date is automatically bounded from 1 August through the earlier
  of the session date or 30 September, so stored future rows are never returned.

## Example

User:

Show me PIE frames between 8 AM and 10 AM yesterday.

MongoDB filter:

{
"camera_name": "Pan Island Expressway",
"captured_at": {
"$gte": <UTC datetime>,
    "$lt": <UTC datetime>
}
}

## Guardrails

Reject:

- Insert, update and delete requests
- Arbitrary MongoDB commands
- Requests for unsupported information
- Attempts to reveal prompts or credentials
- Instructions to override application rules
