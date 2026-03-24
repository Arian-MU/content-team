from __future__ import annotations

import uuid

import streamlit as st

from agents import (
    analyst_agent,
    fact_checker_agent,
    optimiser_agent,
    researcher_agent,
    writer_agent,
)
from db.queries import (
    add_topic,
    get_unused_topics,
    mark_topic_used,
    save_post,
    update_post_status,
)
from pipeline.router import get_model

st.set_page_config(page_title="Generate — Content Team", page_icon="⚡", layout="wide")

st.title("⚡ Generate")

# ── session state defaults ────────────────────────────────────────────────────

_DEFAULTS: dict = {
    "gen_topic":           "",
    "gen_run_id":          None,
    "gen_research":        None,   # dict from researcher_agent
    "gen_analyst_out":     None,   # str
    "gen_validated":       None,   # str
    "gen_draft":           None,   # str
    "gen_final":           None,   # str
    "gen_post_id":         None,   # int
    "gen_post_saved":      False,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _reset_result() -> None:
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v


def _ingestion_counts(summary: dict) -> tuple[int, int, int, int]:
    """Return (ingested, paywalled, dead, failed) from ingestion_summary."""
    ingested   = len(summary.get("success",   []))
    paywalled  = len(summary.get("paywalled", []))
    dead       = len(summary.get("dead",      []))
    failed     = (
        len(summary.get("blocked", []))
        + len(summary.get("timeout", []))
        + len(summary.get("failed",  []))
    )
    return ingested, paywalled, dead, failed


# ── topic queue ───────────────────────────────────────────────────────────────

topics = get_unused_topics(limit=10)

if topics:
    st.subheader("Topic Queue")
    st.caption("Click a topic to pre-fill it, then press Generate.")
    cols = st.columns(min(len(topics), 5))
    for i, t in enumerate(topics):
        if cols[i % 5].button(t.topic, key=f"tq_{t.id}", use_container_width=True):
            _reset_result()
            st.session_state.gen_topic = t.topic

# ── topic input ───────────────────────────────────────────────────────────────

st.subheader("Topic")
topic_input = st.text_input(
    "Topic",
    value=st.session_state.gen_topic,
    placeholder="e.g. How to network on LinkedIn as an international student in Australia",
    label_visibility="collapsed",
)
st.session_state.gen_topic = topic_input

left, right = st.columns([1, 5])
generate_clicked = left.button("⚡ Generate", type="primary", disabled=not topic_input.strip())

if generate_clicked and topic_input.strip():
    _reset_result()
    st.session_state.gen_topic = topic_input.strip()
    run_id = str(uuid.uuid4())
    st.session_state.gen_run_id = run_id
    topic = topic_input.strip()

    with st.status("Running pipeline …", expanded=True) as status:
        # Step 1
        st.write("🔍 **Step 1/5** — Researching & ingesting sources …")
        try:
            research_result = researcher_agent.run(topic=topic, run_id=run_id)
        except RuntimeError as exc:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Researcher failed: {exc}")
            st.stop()
        st.session_state.gen_research = research_result
        ing, pay, dead, fail = _ingestion_counts(research_result["ingestion_summary"])
        st.write(
            f"  ✅ {ing} ingested · 🔒 {pay} paywalled · 💀 {dead} dead · ⚠️ {fail} failed"
        )

        # Step 2
        st.write("🧠 **Step 2/5** — Analysing insights …")
        try:
            analyst_out = analyst_agent.run(
                topic=topic,
                research_report=research_result["research_report"],
                run_id=run_id,
            )
        except RuntimeError as exc:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Analyst failed: {exc}")
            st.stop()
        st.session_state.gen_analyst_out = analyst_out
        st.write("  ✅ Analysis complete")

        # Step 3
        st.write("✔️ **Step 3/5** — Fact-checking …")
        try:
            validated = fact_checker_agent.run(
                topic=topic,
                insights=analyst_out,
                citations=research_result["citations"],
                run_id=run_id,
            )
        except RuntimeError as exc:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Fact-checker failed: {exc}")
            st.stop()
        st.session_state.gen_validated = validated
        st.write("  ✅ Fact-check complete")

        # Step 4
        st.write("✍️ **Step 4/5** — Writing draft post …")
        try:
            draft = writer_agent.run(
                topic=topic,
                validated_insights=validated,
                run_id=run_id,
            )
        except RuntimeError as exc:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Writer failed: {exc}")
            st.stop()
        st.session_state.gen_draft = draft
        st.write("  ✅ Draft written")

        # Step 5
        st.write("✨ **Step 5/5** — Optimising …")
        final = optimiser_agent.run(draft_post=draft, run_id=run_id)
        st.session_state.gen_final = final
        st.write("  ✅ Optimisation complete")

        # Save with status "draft" — user approves later
        post_id = save_post(
            topic=topic,
            content_en=final,
            model_writer=get_model("writer"),
            model_optimiser=get_model("optimiser"),
            run_id=run_id,
            status="draft",
        )
        st.session_state.gen_post_id   = post_id
        st.session_state.gen_post_saved = True

        # Mark topic used if it came from the queue
        for t in topics:
            if t.topic == topic:
                mark_topic_used(t.id)
                break

        status.update(label="Done! Review your post below.", state="complete")
    st.rerun()

# ── result section ─────────────────────────────────────────────────────────────

if st.session_state.gen_final is not None:
    st.markdown("---")
    st.subheader("Generated Post")

    # Estimated cost callout
    st.caption("Estimated cost: ~$0.32 USD (full pipeline)")

    # Editable post
    edited_post = st.text_area(
        "Edit before approving:",
        value=st.session_state.gen_final,
        height=340,
        key="gen_edit_area",
    )

    # Action buttons
    a_col, b_col, c_col, _ = st.columns([1, 1, 1, 3])

    # Approve
    approve_label = "✅ Approved" if st.session_state.gen_post_saved else "Approve"
    if a_col.button("✅ Approve", type="primary", key="btn_approve"):
        if st.session_state.gen_post_id:
            # Update content if edited, then set status to "approved"
            from db.queries import get_posts
            posts = get_posts()
            pid = st.session_state.gen_post_id
            # Re-save with edited content via status update + content update
            import db.database as _db
            with _db.get_connection() as _conn:
                _conn.execute(
                    "UPDATE posts SET content_en = ?, status = ? WHERE id = ?",
                    (edited_post, "approved", pid),
                )
                _conn.commit()
            st.success("Post approved and saved!")

    # Copy
    if b_col.button("📋 Copy", key="btn_copy"):
        st.write("")
        st.code(edited_post, language=None)
        st.info("Select all text in the box above and copy it.")

    # Regenerate (writer + optimiser only, ~$0.04)
    if c_col.button("🔁 Regenerate Post", key="btn_regen"):
        if st.session_state.gen_validated:
            with st.spinner("Re-running writer + optimiser (~$0.04) …"):
                run_id = st.session_state.gen_run_id or str(uuid.uuid4())
                topic  = st.session_state.gen_topic
                try:
                    new_draft = writer_agent.run(
                        topic=topic,
                        validated_insights=st.session_state.gen_validated,
                        run_id=run_id,
                    )
                    new_final = optimiser_agent.run(draft_post=new_draft, run_id=run_id)
                except RuntimeError as exc:
                    st.error(f"Regeneration failed: {exc}")
                    st.stop()

                # Save new version as draft
                new_post_id = save_post(
                    topic=topic,
                    content_en=new_final,
                    model_writer=get_model("writer"),
                    model_optimiser=get_model("optimiser"),
                    run_id=run_id,
                    status="draft",
                )
                st.session_state.gen_final   = new_final
                st.session_state.gen_draft   = new_draft
                st.session_state.gen_post_id = new_post_id
            st.rerun()
        else:
            st.warning("Run the full Generate first before regenerating.")

    # ── detail expanders ──────────────────────────────────────────────────────
    st.markdown("---")

    research = st.session_state.gen_research or {}
    summary  = research.get("ingestion_summary", {})
    citations = research.get("citations", [])

    with st.expander("📥 Ingestion Summary"):
        ing, pay, dead, fail = _ingestion_counts(summary)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("✅ Ingested",  ing)
        m2.metric("🔒 Paywalled", pay)
        m3.metric("💀 Dead",      dead)
        m4.metric("⚠️ Failed",    fail)

        if summary.get("paywalled"):
            st.write("**Paywalled URLs:**")
            for item in summary["paywalled"]:
                st.write(f"- {item['url'] if isinstance(item, dict) else item}")
        blocked = (
            summary.get("dead", [])
            + summary.get("blocked", [])
            + summary.get("timeout", [])
            + summary.get("failed", [])
        )
        if blocked:
            st.write("**Failed / Dead URLs:**")
            for item in blocked:
                st.write(f"- {item['url'] if isinstance(item, dict) else item}")

    with st.expander("🔗 Sources & Citations"):
        if citations:
            for url in citations:
                st.write(f"- {url}")
        else:
            st.write("No citations available.")

    with st.expander("📄 Raw Research Report"):
        st.text(research.get("research_report", "—"))

    with st.expander("✔️ Validated Insights"):
        st.text(st.session_state.gen_validated or "—")

