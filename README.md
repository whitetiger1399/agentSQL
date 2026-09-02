# Camera AgentSQL

A guarded, read-only natural-language query agent for Singapore traffic-camera
frames. It combines a multipage Streamlit UI, OpenAI Responses API structured
output, Pydantic validation, deterministic date/camera resolution, and MongoDB
Atlas.

## Features

- Native Streamlit sidebar/hamburger navigation
- Conversational camera, date, weekday, and time filters
- Camera acronym, alias, and typo matching
- Structured follow-up context
- Read-only, allowlisted PyMongo filters capped at 100 records
- Raw previews for the `cameras` and `traffic_frames` collections
- Singapore-local date interpretation with UTC database bounds

## Setup

Use Python 3.12 and create an isolated environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (already ignored by Git):

```toml
MONGODB_URI = "mongodb+srv://..."
MONGODB_DATABASE = "traffic_agent"
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5.4-mini" # optional

# Optional page content
AUTHOR_NAME = "Your Name"
AUTHOR_BIO = "Your short biography"
CONTACT_EMAIL = "you@example.com"
PROJECT_URL = "https://github.com/you/project"
```

Never commit the real file or expose its contents in logs.

## Run

```bash
streamlit run app.py
```

The Atlas user should have read-only access to the `traffic_agent` database.
The app itself exposes only `find` operations on `cameras` and
`traffic_frames`; all result sets are capped at 100.

## Test

```bash
pytest -q
```

Tests mock external services and do not require live OpenAI or MongoDB access.
