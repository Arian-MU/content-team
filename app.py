from pathlib import Path

import streamlit as st
import yaml

st.set_page_config(
    page_title="Content Team",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── helpers ──────────────────────────────────────────────────────────────────

STRATEGY_PATH = Path("config/strategy.yaml")
_REQUIRED_FIELDS = ["target_audience", "voice_tone", "post_structure"]


def _strategy_is_configured() -> bool:
    """Return True only when the required strategy fields are non-empty."""
    if not STRATEGY_PATH.exists():
        return False
    try:
        data = yaml.safe_load(STRATEGY_PATH.read_text()) or {}
    except yaml.YAMLError:
        return False
    return all(bool(data.get(f)) for f in _REQUIRED_FIELDS)


def _refresh_topics() -> int:
    """Call suggest_topics, persist each suggestion, return count added."""
    from pipeline.crew import suggest_topics
    from db.queries import add_topic

    suggestions = suggest_topics()
    count = 0
    for topic in suggestions:
        topic = topic.strip()
        if topic:
            add_topic(topic, source="ai_suggest")
            count += 1
    return count


# ── first-time redirect ───────────────────────────────────────────────────────

if not _strategy_is_configured():
    st.warning(
        "⚠️ **Strategy not configured.** "
        "Head to **Settings** to fill in your target audience, voice & post structure before generating content."
    )
    st.page_link("pages/4_Settings.py", label="Go to Settings →", icon="⚙️")
    st.stop()

# ── sidebar: refresh topics ───────────────────────────────────────────────────

with st.sidebar:
    st.header("🛠️ Quick Actions")
    if st.button("🔄 Refresh Topic Ideas", use_container_width=True):
        with st.spinner("Generating topic ideas …"):
            try:
                n = _refresh_topics()
                st.success(f"Added {n} new topic{'s' if n != 1 else ''} to the queue.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not refresh topics: {exc}")

# ── main area ────────────────────────────────────────────────────────────────

st.title("✍️ Content Team")
st.markdown(
    "AI-powered LinkedIn content for early-career tech professionals in Australia."
)

col1, col2, col3, col4 = st.columns(4)
col1.page_link("pages/1_Generate.py",       label="Generate",      icon="⚡")
col2.page_link("pages/2_History.py",        label="History",       icon="📋")
col3.page_link("pages/3_Knowledge_Base.py", label="Knowledge Base",icon="📚")
col4.page_link("pages/4_Settings.py",       label="Settings",      icon="⚙️")

st.markdown("---")
st.caption("Select a page from the sidebar or use the quick-links above to get started.")

