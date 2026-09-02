import streamlit as st

from agent_sql.ui import (
    APP_NAME,
    apply_theme,
    architecture_page,
    author_page,
    contact_page,
    docs_page,
    links_page,
    render_sidebar_status,
    schema_page,
    sql_agent_page,
)


st.set_page_config(
    page_title=APP_NAME,
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

pages = {
    "Explore": [
        st.Page(sql_agent_page, title="SQL Agent", icon="💬", default=True),
        st.Page(schema_page, title="Data Schema & Info", icon="🗂️"),
    ],
    "Project": [
        st.Page(docs_page, title="Docs", icon="📖"),
        st.Page(architecture_page, title="Production Architecture", icon="🏗️"),
        st.Page(links_page, title="Links", icon="🔗"),
    ],
    "About": [
        st.Page(author_page, title="Author", icon="👤"),
        st.Page(contact_page, title="Contact Us", icon="✉️"),
    ],
}

navigation = st.navigation(pages, position="sidebar")
st.sidebar.markdown(f"## 🚦 {APP_NAME}")
st.sidebar.caption("Natural-language traffic intelligence")
render_sidebar_status()
navigation.run()
