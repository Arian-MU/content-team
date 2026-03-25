from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

st.set_page_config(page_title="Settings — Content Team", layout="wide")

st.title("Settings")

STRATEGY_PATH = Path("config/strategy.yaml")

# ── helpers ───────────────────────────────────────────────────────────────────

def _load_strategy() -> dict:
    if not STRATEGY_PATH.exists():
        return {}
    try:
        return yaml.safe_load(STRATEGY_PATH.read_text()) or {}
    except yaml.YAMLError:
        return {}


def _save_strategy(data: dict) -> None:
    STRATEGY_PATH.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))


# ── tabs ──────────────────────────────────────────────────────────────────────

tab_strategy, tab_keys, tab_presets = st.tabs(["Strategy", "System & Keys", "Presets"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Strategy
# ══════════════════════════════════════════════════════════════════════════════

with tab_strategy:
    cfg = _load_strategy()

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

        existing_pillars = cfg.get("content_pillars", [])
        content_pillars_raw = st.text_area(
            "Content Pillars (one per line)",
            value="\n".join(existing_pillars),
            height=140,
            help="Key themes for the content. One per line.",
        )

        existing_avoid = cfg.get("topics_to_avoid", [])
        topics_to_avoid_raw = st.text_area(
            "Topics to Avoid (one per line)",
            value="\n".join(existing_avoid) if existing_avoid else "",
            height=80,
        )

        existing_samples = cfg.get("sample_posts", [])
        sample_posts_raw = st.text_area(
            "Sample Posts (paste your own LinkedIn posts, one per line)",
            value="\n".join(existing_samples) if existing_samples else "",
            height=200,
            help="The more samples you provide, the more accurately the AI writes in your voice.",
        )

        submitted = st.form_submit_button("Save Strategy", type="primary")

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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — System & Keys
# ══════════════════════════════════════════════════════════════════════════════

with tab_keys:
    st.subheader("API Key Health")
    st.caption("Click 'Check all keys' to run a live ping against each service.")

    from config.settings import settings as _s

    def _check_anthropic() -> tuple[bool, str]:
        try:
            import anthropic
            anthropic.Anthropic(api_key=_s.ANTHROPIC_API_KEY).models.list()
            return True, "OK"
        except Exception as e:
            return False, str(e)[:120]

    def _check_perplexity() -> tuple[bool, str]:
        try:
            import httpx
            r = httpx.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {_s.PERPLEXITY_API_KEY}"},
                json={"model": "sonar", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                timeout=10,
            )
            r.raise_for_status()
            return True, "OK"
        except Exception as e:
            return False, str(e)[:120]

    def _check_deepseek() -> tuple[bool, str]:
        try:
            import httpx
            r = httpx.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {_s.DEEPSEEK_API_KEY}"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                timeout=10,
            )
            r.raise_for_status()
            return True, "OK"
        except Exception as e:
            return False, str(e)[:120]

    def _check_voyage() -> tuple[bool, str]:
        try:
            import voyageai
            voyageai.Client(api_key=_s.VOYAGE_API_KEY).embed(["test"], model="voyage-3.5")
            return True, "OK"
        except Exception as e:
            return False, str(e)[:120]

    _CHECKS = [
        ("Anthropic (Claude)", "ANTHROPIC_API_KEY", _check_anthropic),
        ("Perplexity", "PERPLEXITY_API_KEY", _check_perplexity),
        ("DeepSeek", "DEEPSEEK_API_KEY", _check_deepseek),
        ("Voyage AI", "VOYAGE_API_KEY", _check_voyage),
    ]

    if "api_health" not in st.session_state:
        st.session_state.api_health = {}

    if st.button("Check all keys", type="primary"):
        with st.spinner("Testing connections..."):
            for name, _key, fn in _CHECKS:
                st.session_state.api_health[name] = fn()

    if st.session_state.api_health:
        st.divider()
        for name, env_key, _ in _CHECKS:
            result = st.session_state.api_health.get(name)
            if result is None:
                continue
            ok, msg = result
            col_icon, col_name, col_msg = st.columns([1, 3, 8])
            col_icon.write("OK" if ok else "FAIL")
            col_name.write(name)
            if not ok:
                col_msg.error(msg)
    else:
        st.caption("No results yet — press 'Check all keys' above.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Presets  (save/load named strategy configs — coming next)
# ══════════════════════════════════════════════════════════════════════════════

with tab_presets:
    st.subheader("Strategy Presets")
    st.info("Save & load named strategy presets — coming next.")

