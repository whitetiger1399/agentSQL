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
- Mongodb database: access user has only read permissions to it
- The LLM agent rejects any write or modify attempts
- even if the user at some later stage tries to surpass the LLM agent
- the mongodb user with only read persmission will not allow any modification
