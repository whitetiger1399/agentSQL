# AgentSQL Project Instructions

## Project objective

Build a natural-language traffic-camera database query agent for a take-home assignment.

The application must support:

- Camera names, acronyms, aliases and reasonable typos
- Exact, relative and ranged dates
- Time ranges and recurring weekdays
- Conversational follow-ups
- Read-only database access
- Prompt-injection and malicious-query guardrails

## Technology stack

- Python 3.12
- Streamlit
- OpenAI Responses API with structured output
- Pydantic
- MongoDB Atlas and PyMongo
- RapidFuzz
- pytest
- Asia/Singapore timezone

Avoid unnecessary agent frameworks and abstractions.

## Database

Database name: `traffic_agent`

Collections:

### cameras

Fields:

- `camera_id`: integer
- `camera_name`: canonical string
- `acronym`: string
- `aliases`: string array
- `active`: boolean

### traffic_frames

Native MongoDB time-series collection:

- timeField: `captured_at`
- metaField: `camera_name`
- granularity: `minutes`

Fields:

- `frame_id`: integer
- `captured_at`: BSON UTC Date
- `camera_name`: canonical string
- `frame_img_url`: string

The sample dataset contains 7,920 hourly frame records covering
1 August through 2 September 2026.

## Implementation rules

- Store database timestamps in UTC.
- Interpret user dates using `Asia/Singapore`.
- Never allow the LLM to generate or execute MongoDB queries directly.
- The LLM may only produce a validated structured query plan.
- Build MongoDB filters deterministically in Python.
- Only permit read operations.
- Limit results to 100 records.
- Maintain conversation context as structured filters.
- Never commit API keys, database credentials or connection strings.
- Run tests after changing camera, date or query-resolution logic.
