# Camera AgentSQL

A guarded, read-only natural-language query agent for Singapore traffic-camera
frames. It combines a multipage Streamlit UI, OpenAI Responses API structured
output, Pydantic validation, deterministic date/camera resolution, and MongoDB
Atlas.

## Live App

The Streamlit application has been deployed and is available here for review:

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://sql-agent-by-wt.streamlit.app/)

**[Launch Camera AgentSQL](https://sql-agent-by-wt.streamlit.app/)**

> If the OpenAI rate limit has been reached, or OpenAI is temporarily
> unresponsive because of token limits or another API issue, please feel free
> to reach out through the app's **Author & Contact** page.

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
MONGODB_URI = "YOUR_MONGODB_ATLAS_CONNECTION_STRING"
MONGODB_DATABASE = "assignement01"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
OPENAI_MODEL = "gpt-5.4-mini" # optional

# Optional page content
AUTHOR_NAME = "Ritik Srivastava"
AUTHOR_BIO = "Developer of Camera AgentSQL"
CONTACT_EMAIL = "ritiksrivastava144@gmail.com"
AUTHOR_LINKEDIN = "https://www.linkedin.com/in/ritik999/"
PROJECT_URL = "https://github.com/you/project"
```

Never commit the real file or expose its contents in logs.

Use `.streamlit/secrets.example.toml` as the key-name template. It contains
placeholders only and is safe to commit.

## Run

```bash
streamlit run app.py
```

The Atlas user should have read-only access to the `assignement01` database.
The app itself exposes only `find` operations on `cameras` and
`traffic_frames`; all result sets are capped at 100.

## Test

```bash
pytest -q
```

Tests mock external services and do not require live OpenAI or MongoDB access.

## Deploy with Streamlit Community Cloud

GitHub hosts the source code; Streamlit Community Cloud runs the Python app.

1. Push the repository to GitHub with `.streamlit/secrets.toml` still ignored.
2. In Streamlit Community Cloud, create an app from this repository and select
   `app.py` as the entry point.
3. Open **Advanced settings → Secrets** and paste the real values using the same
   TOML keys shown in `.streamlit/secrets.example.toml`.
4. Deploy the app. Streamlit injects those values into `st.secrets` at runtime;
   they are not added to the GitHub repository.
5. Allow Streamlit Cloud's outbound access in MongoDB Atlas. For a demo, Atlas
   can temporarily permit `0.0.0.0/0` only when the database user is strictly
   read-only and uses a strong password. Restrict network access further for a
   production deployment.

Before every push, verify the real secret file is ignored:

```bash
git check-ignore .streamlit/secrets.toml
git ls-files .streamlit/secrets.toml
```

The first command should print the filename; the second should print nothing.
