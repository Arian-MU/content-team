from pathlib import Path

import streamlit as st
import yaml

from db.database import init_db

# Ensure all SQLite tables exist on every startup (no-op if already created)
init_db()

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


def _parse_topic_line(line: str) -> dict:
    """Parse a raw topic agent line into {title, why, source_url}.

    Expected format: "N. Title | Why now | URL or search: query"
    Handles malformed lines by falling back gracefully.
    """
    # Strip leading number + dot (e.g. "1. ")
    text = line.strip()
    if text and text[0].isdigit():
        dot = text.find(".")
        if dot != -1:
            text = text[dot + 1:].strip()

    parts = [p.strip() for p in text.split("|")]
    title      = parts[0] if len(parts) > 0 else text
    why        = parts[1] if len(parts) > 1 else ""
    source_url = parts[2] if len(parts) > 2 else ""

    # Treat "search: …" entries as display-only (no real URL)
    if source_url.lower().startswith("search:"):
        source_url = ""

    return {"title": title, "why": why, "source_url": source_url}


def _fetch_suggestions() -> list[dict]:
    """Call topic_agent, parse all 10 lines, return list of dicts."""
    from pipeline.crew import suggest_topics
    raw_lines = suggest_topics()
    return [_parse_topic_line(line) for line in raw_lines if line.strip()]


# ── session state defaults ────────────────────────────────────────────────────

if "topic_suggestions" not in st.session_state:
    st.session_state.topic_suggestions = None   # list[dict] | None


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
                st.session_state.topic_suggestions = _fetch_suggestions()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not generate topics: {exc}")
        st.rerun()

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

# ── topic suggestion cards ────────────────────────────────────────────────────

suggestions: list[dict] | None = st.session_state.topic_suggestions

if suggestions:
    st.subheader("💡 Topic Suggestions")
    st.caption("Review the ideas below, check the ones you want to queue, then save.")

    for i, s in enumerate(suggestions):
        with st.container(border=True):
            checked = st.checkbox(
                f"**{s['title']}**",
                key=f"tsugg_{i}",
                value=True,
            )
            if s["why"]:
                st.caption(f"📌 {s['why']}")
            if s["source_url"]:
                st.markdown(f"🔗 [{s['source_url']}]({s['source_url']})")

    st.markdown("")
    save_col, dismiss_col, _ = st.columns([1, 1, 4])

    if save_col.button("✅ Save Selected", type="primary"):
        from db.queries import add_topic
        saved = 0
        for i, s in enumerate(suggestions):
            if st.session_state.get(f"tsugg_{i}", False):
                add_topic(
                    topic=s["title"],
                    source="ai_suggest",
                    source_url=s["source_url"] or None,
                )
                saved += 1
        st.session_state.topic_suggestions = None
        st.success(f"Saved {saved} topic{'s' if saved != 1 else ''} to the queue. Head to Generate to use them.")
        st.rerun()

    if dismiss_col.button("✖ Dismiss"):
        st.session_state.topic_suggestions = None
        st.rerun()

else:
    st.caption("Select a page from the sidebar or use the quick-links above. Use **🔄 Refresh Topic Ideas** in the sidebar to generate new suggestions.")

