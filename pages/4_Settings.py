from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

st.set_page_config(page_title="Settings — Content Team", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings")

STRATEGY_PATH = Path("config/strategy.yaml")

# ── load current strategy ─────────────────────────────────────────────────────

def _load_strategy() -> dict:
    if not STRATEGY_PATH.exists():
        return {}
    try:
        return yaml.safe_load(STRATEGY_PATH.read_text()) or {}
    except yaml.YAMLError:
        return {}


def _save_strategy(data: dict) -> None:
    STRATEGY_PATH.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))


cfg = _load_strategy()

# ── form ──────────────────────────────────────────────────────────────────────

st.subheader("Content Strategy")
st.caption("These settings are injected into every agent prompt.")

with st.form("strategy_form"):
    target_audience = st.text_area(
        "Target Audience *",
        value=cfg.get("target_audience", ""),
        height=80,
        help="Who is this content for? Be specific.",
    )

    voice_tone = st.text_area(
        "Voice & Tone *",
        value=cfg.get("voice_tone", ""),
        height=80,
        help="How should the writing sound? e.g. conversational, first-person, honest.",
    )

    post_structure = st.text_input(
        "Post Structure *",
        value=cfg.get("post_structure", ""),
        help="e.g. Hook -> Observation -> Insight -> Takeaway -> CTA -> Hashtags",
    )

    hashtag_strategy = st.text_input(
        "Hashtag Strategy",
        value=cfg.get("hashtag_strategy", ""),
        help="e.g. 3-5 hashtags, mix broad and niche.",
    )

    max_post_length = st.number_input(
        "Max Post Length (words)",
        min_value=50,
        max_value=1000,
        value=int(cfg.get("max_post_length", 250)),
        step=25,
    )

    # Content pillars
    existing_pillars = cfg.get("content_pillars", [])
    content_pillars_raw = st.text_area(
        "Content Pillars (one per line)",
        value="\n".join(existing_pillars),
        height=140,
        help="Key themes for the content. One per line.",
    )

    # Topics to avoid
    existing_avoid = cfg.get("topics_to_avoid", [])
    topics_to_avoid_raw = st.text_area(
        "Topics to Avoid (one per line)",
        value="\n".join(existing_avoid) if existing_avoid else "",
        height=80,
    )

    # Sample posts
    existing_samples = cfg.get("sample_posts", [])
    sample_posts_raw = st.text_area(
        "Sample Posts (paste your own LinkedIn posts, one per line)",
        value="\n".join(existing_samples) if existing_samples else "",
        height=200,
        help="The more samples you provide, the more accurately the AI writes in your voice.",
    )

    submitted = st.form_submit_button("💾 Save Strategy", type="primary")

if submitted:
    if not target_audience.strip() or not voice_tone.strip() or not post_structure.strip():
        st.error("Please fill in all required fields (marked with *).")
    else:
        new_cfg = {
            "target_audience":   target_audience.strip(),
            "voice_tone":        voice_tone.strip(),
            "content_pillars":   [p.strip() for p in content_pillars_raw.splitlines() if p.strip()],
            "topics_to_avoid":   [t.strip() for t in topics_to_avoid_raw.splitlines() if t.strip()],
            "post_structure":    post_structure.strip(),
            "hashtag_strategy":  hashtag_strategy.strip(),
            "max_post_length":   int(max_post_length),
            "sample_posts":      [s.strip() for s in sample_posts_raw.splitlines() if s.strip()],
        }
        _save_strategy(new_cfg)
        st.success("Strategy saved! You can now generate content.")
        st.rerun()

