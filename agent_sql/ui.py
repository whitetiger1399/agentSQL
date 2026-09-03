from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import streamlit as st

from .config import ConfigurationError, Settings
from .database import DatabaseUnavailable, MongoRepository
from .llm import OpenAIPlanner
from .models import AgentResult, SessionContext
from .pipeline import run_query


APP_NAME = "Camera AgentSQL"


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 4rem; max-width: 1500px;}
        [data-testid="stSidebar"] {border-right: 1px solid rgba(125,125,125,.18);}
        .hero {
            padding: 1.5rem 1.65rem; border: 1px solid rgba(125,125,125,.2);
            border-radius: 18px; background: linear-gradient(135deg, rgba(30,136,229,.12), rgba(0,200,160,.08));
            margin-bottom: 1.2rem;
        }
        .hero h1 {font-size: 2rem; margin: 0 0 .35rem 0;}
        .hero p {margin: 0; color: #8492a6;}
        .agent-header {
            display: flex; align-items: baseline; gap: .8rem; padding: .45rem 0 .6rem;
            border-bottom: 1px solid rgba(125,125,125,.18); margin-bottom: .65rem;
        }
        .agent-header h1 {font-size: 1.65rem; margin: 0; white-space: nowrap;}
        .agent-header p {margin: 0; color: #8492a6; font-size: .92rem;}
        .session-date {
            margin-left: auto; white-space: nowrap; color: #35D5C4;
            font-size: .78rem; font-weight: 600; text-align: right;
        }
        .eyebrow {font-size: .76rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #29b6a6;}
        .status-pill {padding: .35rem .65rem; border-radius: 999px; border: 1px solid rgba(125,125,125,.25); font-size: .8rem;}
        div[data-testid="stChatMessage"] {
            border: 1px solid rgba(125,125,125,.15); border-radius: 16px;
            padding: .3rem .65rem; margin-bottom: .7rem; max-width: 88%;
            box-shadow: 0 5px 16px rgba(0,0,0,.08);
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            margin-left: 12%; margin-right: 0; background: rgba(25,168,154,.16);
            border-color: rgba(25,168,154,.35); flex-direction: row-reverse;
            border-bottom-right-radius: 5px;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
        [data-testid="stChatMessageContent"] {
            text-align: right; padding-right: .45rem;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
        [data-testid="stChatMessageContent"] p {
            text-align: right;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            margin-left: 0; margin-right: 12%; background: rgba(30,45,68,.72);
            border-bottom-left-radius: 5px;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])
        [data-testid="stChatMessageContent"] {
            text-align: left;
        }
        div[data-testid="stChatInput"] {
            border-radius: 18px; width: 100%; margin-top: -.55rem;
            position: sticky; bottom: .5rem; z-index: 20;
            background: #0B1220; padding: .2rem;
            border: 2px solid #19A89A;
            overflow: hidden; box-sizing: border-box;
            box-shadow: 0 0 0 1px rgba(25,168,154,.2), 0 7px 22px rgba(0,0,0,.22);
            transition: border-color .18s ease, box-shadow .18s ease;
        }
        div[data-testid="stChatInput"]:focus-within {
            border-color: #35D5C4;
            box-shadow: 0 0 0 3px rgba(25,168,154,.24), 0 8px 24px rgba(0,0,0,.28);
        }
        div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            border: 0 !important; box-shadow: none !important;
            outline: 0 !important; border-radius: 14px !important;
        }
        div[data-testid="stChatInput"] textarea {
            min-height: 48px; outline: 0 !important; box-shadow: none !important;
        }
        .chat-row {display: flex; width: 100%; gap: .55rem; align-items: flex-end; margin: .75rem 0;}
        .chat-row.agent {justify-content: flex-start; padding-right: 12%;}
        .chat-row.human {justify-content: flex-end; padding-left: 12%;}
        .chat-avatar {
            display: flex; align-items: center; justify-content: center; flex: 0 0 34px;
            width: 34px; height: 34px; border-radius: 50%; font-size: 1rem;
            background: #1c2b41; border: 1px solid rgba(255,255,255,.12);
        }
        .chat-row.human .chat-avatar {background: #168f84; order: 2;}
        .chat-bubble {
            max-width: calc(100% - 44px); padding: .7rem .9rem; line-height: 1.45;
            border: 1px solid rgba(125,125,125,.2); box-shadow: 0 5px 16px rgba(0,0,0,.08);
        }
        .agent-bubble {
            text-align: left; background: rgba(30,45,68,.82);
            border-radius: 16px 16px 16px 5px;
        }
        .human-bubble {
            text-align: right; background: rgba(25,168,154,.2);
            border-color: rgba(25,168,154,.4); border-radius: 16px 16px 5px 16px;
        }
        @media (max-width: 900px) {
            .block-container {padding-left: 1rem; padding-right: 1rem; padding-top: .75rem;}
            .agent-header {display: block;}
            .agent-header p {margin-top: .2rem;}
            .session-date {margin-top: .3rem; text-align: left;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, description: str, eyebrow: str = "TRAFFIC INTELLIGENCE") -> None:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>',
        unsafe_allow_html=True,
    )


def secret_values() -> dict[str, Any]:
    return dict(st.secrets)


@st.cache_resource(show_spinner=False)
def repository(uri: str, database: str) -> MongoRepository:
    return MongoRepository(uri, database)


@st.cache_resource(show_spinner=False)
def planner(api_key: str, model: str) -> OpenAIPlanner:
    return OpenAIPlanner(api_key, model)


def optional_content(key: str, fallback: str) -> str:
    value = secret_values().get(key)
    return str(value).strip() if value else fallback


def get_repository() -> MongoRepository:
    values = secret_values()
    uri = str(values.get("MONGODB_URI", "")).strip()
    database = str(values.get("MONGODB_DATABASE", "")).strip()
    if not uri or not database:
        raise ConfigurationError("Add MONGODB_URI and MONGODB_DATABASE to .streamlit/secrets.toml.")
    return repository(uri, database)


def get_settings() -> Settings:
    return Settings.from_mapping(secret_values())


def render_sidebar_status() -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption("SERVICE STATUS")
    try:
        get_repository().ping()
        st.sidebar.success("MongoDB connected", icon="✅")
    except (ConfigurationError, DatabaseUnavailable):
        st.sidebar.warning("MongoDB unavailable", icon="⚠️")
    if str(secret_values().get("OPENAI_API_KEY", "")).strip():
        st.sidebar.success("OpenAI configured", icon="✅")
    else:
        st.sidebar.warning("OpenAI key missing", icon="⚠️")
    st.sidebar.caption("Read-only • Asia/Singapore • 100-row limit")


def docs_page() -> None:
    hero("Documentation", "How to ask safe, useful questions about traffic-camera frames.")
    st.subheader("Ask naturally")
    st.markdown(
        """
        Try requests such as:

        - `Show me PIE frames between 8 AM and 10 AM yesterday.`
        - `Find CTE cameras last Monday.`
        - `Now only show frames after 6 PM.`

        The agent understands camera names, acronyms, aliases, common typos, date ranges,
        relative dates, weekdays, time windows, and contextual follow-ups.
        """
    )
    st.subheader("Safety model")
    st.info(
        "The language model creates a validated plan only. Python resolves it and builds an allowlisted, read-only MongoDB filter."
    )


def architecture_page() -> None:
    hero("Production Architecture", "A constrained path from natural language to read-only results.")
    st.code(
        """User → scope guardrail → OpenAI structured QueryPlan → Pydantic validation
     → camera/date/context resolver → deterministic filter builder
     → read-only PyMongo repository → capped results → Streamlit UI""",
        language="text",
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Query limit", "100 rows")
    c2.metric("Application timezone", "Asia/Singapore")
    c3.metric("Database writes", "Disabled")
    st.subheader("Boundary controls")
    st.markdown(
        "- Strict structured output; extra fields are rejected.\n"
        "- Camera values resolve against canonical database metadata.\n"
        "- Only `$and`, `$or`, `$in`, `$gte`, and `$lt` may reach `find`.\n"
        "- Secrets never enter model context or user-visible errors."
    )


def links_page() -> None:
    hero("Links", "Project resources and reference material.")
    links = {
        "Project repository": optional_content("PROJECT_URL", "https://github.com/your-account/agent-sql"),
        "OpenAI Responses API": "https://developers.openai.com/api/docs/guides/migrate-to-responses",
        "Streamlit documentation": "https://docs.streamlit.io",
        "MongoDB time series": "https://www.mongodb.com/docs/manual/core/timeseries-collections/",
    }
    for label, url in links.items():
        st.markdown(f"**{label}**  \n{url}")


def author_page() -> None:
    hero("Author", "The person behind Camera AgentSQL.")
    name = optional_content("AUTHOR_NAME", "Your Name")
    bio = optional_content(
        "AUTHOR_BIO",
        "Add AUTHOR_NAME and AUTHOR_BIO to Streamlit secrets to personalize this page.",
    )
    st.subheader(name)
    st.write(bio)


def contact_page() -> None:
    hero("Contact Us", "Questions, feedback, or collaboration.")
    email = optional_content("CONTACT_EMAIL", "hello@example.com")
    st.subheader("Get in touch")
    st.write("For project questions or feedback, reach out by email.")
    st.link_button(f"Email {email}", f"mailto:{email}")
    st.caption("Set CONTACT_EMAIL in Streamlit secrets to replace this placeholder.")


def schema_page() -> None:
    hero("Data Schema & Info", "The read-only collections available to the agent.")
    tab1, tab2 = st.tabs(["cameras", "traffic_frames"])
    with tab1:
        st.markdown(
            """
            | Field | Type | Description |
            |---|---|---|
            | `camera_id` | integer | Stable camera identifier |
            | `camera_name` | string | Canonical camera name |
            | `acronym` | string | Common short name |
            | `aliases` | string[] | Alternate names |
            | `active` | boolean | Availability flag |
            """
        )
    with tab2:
        st.markdown(
            """
            MongoDB native time-series collection (`captured_at` time field,
            `camera_name` metadata field, minute granularity).

            | Field | Type | Description |
            |---|---|---|
            | `frame_id` | integer | Stable frame identifier |
            | `captured_at` | BSON UTC Date | Capture timestamp |
            | `camera_name` | string | Canonical camera name |
            | `frame_img_url` | string | Frame image location |
            """
        )
    st.info("The sample dataset contains 7,920 hourly records from 1 August to 2 September 2026.")


def _initial_chat() -> list[dict[str, Any]]:
    return [
        {
            "role": "assistant",
            "message": "Ask me to find traffic-camera frames by camera, date, weekday, or time.",
            "result": None,
        }
    ]


def _render_chat_bubble(role: str, message: str) -> None:
    safe_message = html.escape(message).replace("\n", "<br>")
    if role == "user":
        st.markdown(
            f'<div class="chat-row human"><div class="chat-bubble human-bubble">{safe_message}</div>'
            '<div class="chat-avatar" aria-label="User">👤</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="chat-row agent"><div class="chat-avatar" aria-label="Agent">🤖</div>'
            f'<div class="chat-bubble agent-bubble">{safe_message}</div></div>',
            unsafe_allow_html=True,
        )


def _render_result(result_data: Mapping[str, Any]) -> None:
    result = AgentResult.model_validate(result_data)
    if result.interpreted_filters:
        with st.expander("Interpreted filters", expanded=False):
            st.json(result.interpreted_filters)
    if result.suggestions:
        st.caption("Suggestions: " + " · ".join(result.suggestions))
    if result.records:
        st.dataframe(result.records, use_container_width=True, hide_index=True)


def _collection_panel(repo: MongoRepository | None) -> None:
    st.markdown("### Data explorer")
    st.caption("Read-only preview · first 100 documents")
    if repo is None:
        st.warning("Configure MongoDB secrets to preview collections.")
        return
    if "selected_collection" not in st.session_state:
        st.session_state.selected_collection = "cameras"
    for name in repo.list_allowed_collections():
        if st.button(
            name,
            key=f"collection_{name}",
            use_container_width=True,
            type="primary" if st.session_state.selected_collection == name else "secondary",
        ):
            st.session_state.selected_collection = name
    try:
        with st.spinner("Loading preview…"):
            rows = repo.preview_collection(st.session_state.selected_collection, limit=100)
        st.caption(
            f"Showing the top {len(rows)} row{'s' if len(rows) != 1 else ''} "
            f"from `{st.session_state.selected_collection}` (maximum 100)."
        )
        if rows:
            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
                height=520,
                key=f"preview_{st.session_state.selected_collection}",
            )
        else:
            st.info("This collection is empty.")
    except DatabaseUnavailable as exc:
        st.error(str(exc))


def _processing_panel() -> None:
    st.markdown("### Query processing")
    st.caption("Safe operational trace · no hidden reasoning or secrets")
    latest_result: AgentResult | None = None
    for item in reversed(st.session_state.get("chat_messages", [])):
        if item.get("role") == "assistant" and item.get("result"):
            latest_result = AgentResult.model_validate(item["result"])
            break
    if latest_result is None or not latest_result.processing_steps:
        st.info("Run a query to inspect each processing step.")
        return

    status_icons = {
        "passed": "✅",
        "completed": "✅",
        "rejected": "⛔",
        "error": "⚠️",
    }
    st.caption(f"Final status: **{latest_result.status.upper()}**")
    for index, step in enumerate(latest_result.processing_steps):
        icon = status_icons[step.status]
        with st.expander(
            f"{icon} {step.name}",
            expanded=index == len(latest_result.processing_steps) - 1,
        ):
            st.json(step.details)


def sql_agent_page() -> None:
    if "session_now_utc" not in st.session_state:
        st.session_state.session_now_utc = datetime.now(timezone.utc).isoformat()
    session_now = datetime.fromisoformat(st.session_state.session_now_utc)
    session_date = session_now.astimezone(ZoneInfo("Asia/Singapore")).strftime(
        "%d %b %Y, %I:%M %p SGT"
    )
    st.markdown(
        '<div class="agent-header"><h1>SQL Agent</h1>'
        '<p>Natural language → guarded, read-only MongoDB queries</p>'
        f'<div class="session-date">Session date · {session_date}</div></div>',
        unsafe_allow_html=True,
    )
    try:
        repo: MongoRepository | None = get_repository()
    except (ConfigurationError, DatabaseUnavailable):
        repo = None

    chat_col, data_col = st.columns([1.9, 1], gap="medium")
    with chat_col:
        title_col, clear_col = st.columns([4, 1])
        title_col.markdown("### Conversation")
        if clear_col.button("Clear", use_container_width=True):
            st.session_state.chat_messages = _initial_chat()
            st.session_state.query_context = SessionContext().model_dump(mode="json")
            st.rerun()
        st.caption("Examples: “PIE yesterday 8–10 AM” · “Mondays in August” · “Now after 6 PM”")
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = _initial_chat()
        if "query_context" not in st.session_state:
            st.session_state.query_context = SessionContext().model_dump(mode="json")
        conversation = st.container(height=400, border=True)
        with conversation:
            for item in st.session_state.chat_messages:
                _render_chat_bubble(item["role"], item["message"])
                if item.get("result"):
                    _render_result(item["result"])

        message = st.chat_input("Ask about traffic-camera frames…")
        if message:
            st.session_state.chat_messages.append({"role": "user", "message": message, "result": None})
            try:
                settings = get_settings()
                if repo is None:
                    raise ConfigurationError("MongoDB is not configured.")
                with st.spinner("Interpreting and querying safely…"):
                    result = run_query(
                        message,
                        SessionContext.model_validate(st.session_state.query_context),
                        planner(settings.openai_api_key, settings.openai_model),
                        repo,
                        now=session_now,
                    )
            except ConfigurationError as exc:
                result = AgentResult(
                    status="error",
                    message=str(exc),
                    context=SessionContext.model_validate(st.session_state.query_context),
                )
            st.session_state.query_context = result.context.model_dump(mode="json")
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "message": result.message,
                    "result": result.model_dump(mode="json"),
                }
            )
            st.rerun()
    with data_col:
        explorer_tab, processing_tab = st.tabs(["Data Explorer", "Query Processing"])
        with explorer_tab:
            _collection_panel(repo)
        with processing_tab:
            _processing_panel()
