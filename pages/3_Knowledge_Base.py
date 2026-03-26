from __future__ import annotations

import re
import uuid

import streamlit as st

from db.queries import save_research_output
from pipeline.crew import run_from_research
from rag.chromadb_client import get_doc_count, get_sources
from rag.fetcher import fetch_article
from rag.ingestor import ingest_url


# ── helpers ────────────────────────────────────────────────────────────────────

def _parse_research_md(text: str) -> tuple[str, list[str], list[str]]:
    """Return (title, urls, citations) parsed from a markdown research report.

    title     — first H1/H2 heading, or first non-empty line as fallback.
    urls      — all unique https:// URLs found in the text (may be empty for
                ChatGPT Deep Research exports where URLs aren't in the markdown).
    citations — References/Sources section bullet points, or urls if no section
                found. These are passed downstream as the citations list.

    Handles two ChatGPT export formats:
      • 【14†L583-L592】 inline citation markers (Deep Research .md)
      • citeturnXXview0  inline citation markers (canvas/research mode)
    Both are stripped from the returned title and citation strings.
    """
    # ── Title: first non-empty heading or line ────────────────────────────────
    title = ""
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        stripped = re.sub(r'【\d+†[^\】]*】', '', stripped).strip()  # strip 【N†...】
        stripped = re.sub(r'citeturn\w+', '', stripped).strip()       # strip citeturnX
        if stripped:
            title = stripped
            break

    # ── Bare URLs ─────────────────────────────────────────────────────────────
    urls: list[str] = []
    seen_urls: set[str] = set()
    for url in re.findall(r'https?://[^\s\)\]"\'>,]+', text):
        url = url.rstrip(".,;)")
        if url not in seen_urls:
            seen_urls.add(url)
            urls.append(url)

    # ── References / Sources section ─────────────────────────────────────────
    # Look for a heading like ## References, ## Sources, ## Bibliography
    ref_section_re = re.compile(
        r'^#{1,3}\s*(references?|sources?|bibliography|citations?)\s*$',
        re.IGNORECASE | re.MULTILINE,
    )
    citations: list[str] = []
    match = ref_section_re.search(text)
    if match:
        ref_text = text[match.end():]
        # Collect bullet/numbered lines until the next heading
        next_heading = re.search(r'^#{1,3}\s', ref_text, re.MULTILINE)
        if next_heading:
            ref_text = ref_text[:next_heading.start()]
        for line in ref_text.splitlines():
            # Strip leading list markers (-, *, •, 1., etc.)
            clean = re.sub(r'^[\s\-\*•\d\.]+', '', line).strip()
            # Strip ChatGPT citation markers
            clean = re.sub(r'【\d+†[^\】]*】', '', clean).strip()
            clean = re.sub(r'citeturn\w+', '', clean).strip()
            if clean:
                citations.append(clean)

    # Fall back to bare URLs if no references section found
    if not citations:
        citations = urls

    return title, urls, citations



st.set_page_config(page_title="Knowledge Base — Content Team", page_icon="📚", layout="wide")

st.title("📚 Knowledge Base")

# ── metrics ───────────────────────────────────────────────────────────────────

st.subheader("Collection Stats")
m1, m2, m3, m4 = st.columns(4)
m1.metric("📰 Articles",        get_doc_count("article"))
m2.metric("💼 LinkedIn Posts",  get_doc_count("linkedin_post"))
m3.metric("🔬 Research Papers", get_doc_count("research_paper"))
m4.metric("📦 Total Chunks",    get_doc_count())

st.markdown("---")

# ── browse sources ────────────────────────────────────────────────────────────

st.subheader("Browse Sources")

_CAT_OPTIONS = ["All", "article", "linkedin_post", "research_paper"]
filter_col, search_col = st.columns([2, 4])
cat_filter   = filter_col.selectbox("Filter by category", _CAT_OPTIONS, key="kb_cat_filter")
search_query = search_col.text_input("Search title / URL", placeholder="Type to filter…", key="kb_search")

sources = get_sources(category=None if cat_filter == "All" else cat_filter)

# Apply text search
if search_query.strip():
    q = search_query.strip().lower()
    sources = [s for s in sources if q in s["title"].lower() or q in s["source_url"].lower()]

if not sources:
    st.info("No sources found. Run the pipeline or add URLs below to populate the knowledge base.")
else:
    st.caption(f"Showing **{len(sources)}** unique source(s)")
    for s in sources:
        label = s["title"] if s["title"] != s["source_url"] else s["source_url"]
        with st.expander(f"**{label[:90]}**  ·  `{s['category']}`  ·  {s['ingested_at']}", expanded=False):
            st.markdown(f"🔗 [{s['source_url']}]({s['source_url']})")
            cols = st.columns(3)
            cols[0].caption(f"**Category:** {s['category']}")
            cols[1].caption(f"**Ingested by:** {s['ingested_by']}")
            cols[2].caption(f"**Run ID:** `{s['run_id'][:8]}…`" if s["run_id"] else "**Run ID:** —")

st.markdown("---")

# ── add single URL ────────────────────────────────────────────────────────────

st.subheader("Add Single URL")

url_col, cat_col, btn_col = st.columns([4, 2, 1])
single_url      = url_col.text_input("URL", placeholder="https://example.com/article", label_visibility="collapsed")
single_category = cat_col.selectbox(
    "Category", ["article", "linkedin_post", "research_paper"], label_visibility="collapsed"
)

if btn_col.button("➕ Add", type="primary", disabled=not single_url.strip()):
    with st.spinner("Fetching and ingesting …"):
        result = fetch_article(single_url.strip())
        if result["status"] != "success":
            st.error(f"Could not fetch URL ({result['status']}): {result.get('reason', '')}")
        else:
            ok = ingest_url(
                url=result["url"],
                content=result["content"],
                title=result["title"] or result["url"],
                category=single_category,
                ingested_by="manual",
                run_id=str(uuid.uuid4()),
            )
            if ok:
                st.success(f"Ingested: **{result['title'] or result['url']}**")
            else:
                st.info("Already in the knowledge base (duplicate skipped).")
    st.rerun()

st.markdown("---")

# ── batch upload (.txt with one URL per line) ─────────────────────────────────

st.subheader("Batch Upload")
st.caption("Upload a plain `.txt` file with one URL per line.")

batch_col, bcat_col = st.columns([4, 2])
uploaded_file    = batch_col.file_uploader("URL list (.txt)", type=["txt"], label_visibility="collapsed")
batch_category   = bcat_col.selectbox(
    "Category", ["article", "linkedin_post", "research_paper"],
    key="batch_cat", label_visibility="collapsed"
)

if uploaded_file is not None:
    urls = [
        line.strip()
        for line in uploaded_file.read().decode("utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    st.write(f"Found **{len(urls)}** URL(s) in file.")

    if st.button("⬆️ Ingest All", type="primary"):
        progress_bar = st.progress(0, text="Starting …")
        ingested = skipped = failed = 0
        run_id = str(uuid.uuid4())

        for idx, url in enumerate(urls):
            progress_bar.progress((idx) / len(urls), text=f"Processing {idx + 1}/{len(urls)} …")
            result = fetch_article(url)
            if result["status"] == "success":
                ok = ingest_url(
                    url=result["url"],
                    content=result["content"],
                    title=result["title"] or url,
                    category=batch_category,
                    ingested_by="batch_upload",
                    run_id=run_id,
                )
                if ok:
                    ingested += 1
                else:
                    skipped += 1
            else:
                failed += 1

        progress_bar.progress(1.0, text="Done!")
        st.success(
            f"Batch complete — ✅ {ingested} ingested · ⏭️ {skipped} duplicates skipped · ⚠️ {failed} failed"
        )
        st.rerun()

st.markdown("---")

# ── upload external research report (.md) ─────────────────────────────────────

st.subheader("Upload Research Report")
st.caption(
    "Paste in or upload a **Markdown research report** (e.g. from ChatGPT Deep Research) "
    "to ingest it into the knowledge base and generate a LinkedIn post — no Perplexity API needed."
)

# ── session state for this section ───────────────────────────────────────────
if "rr_parsed" not in st.session_state:
    st.session_state.rr_parsed = None   # dict with title/urls/text/run_id or None
if "rr_result" not in st.session_state:
    st.session_state.rr_result = None   # dict from run_from_research or None

rr_col_file, rr_col_paste = st.columns([1, 1])

with rr_col_file:
    rr_file = st.file_uploader(
        "Upload .md file", type=["md", "txt"], key="rr_uploader",
        label_visibility="collapsed",
    )
with rr_col_paste:
    rr_paste = st.text_area(
        "…or paste report text here",
        height=140,
        placeholder="# My Research Report\n\nPaste the full markdown here …",
        key="rr_paste_text",
        label_visibility="collapsed",
    )

# Resolve source: file beats paste
rr_raw_text: str = ""
if rr_file is not None:
    rr_raw_text = rr_file.read().decode("utf-8", errors="replace")
elif rr_paste.strip():
    rr_raw_text = rr_paste.strip()

if rr_raw_text:
    auto_title, found_urls, found_citations = _parse_research_md(rr_raw_text)

    st.markdown("**Preview**")
    url_label = f"🔗 {len(found_urls)} URL(s)" if found_urls else "🔗 No bare URLs (ChatGPT export format)"
    ref_label = f"📚 {len(found_citations)} reference(s) extracted" if found_citations else "📚 No references section found"
    st.info(f"📄 {len(rr_raw_text):,} characters · {url_label} · {ref_label}")
    with st.expander("Show extracted references / citations"):
        if found_citations:
            for c in found_citations:
                st.markdown(f"- {c}")
        elif found_urls:
            for u in found_urls:
                st.markdown(f"- {u}")
        else:
            st.caption("No references or URLs found. The full report text will still be ingested.")

    topic_input = st.text_input(
        "Topic for this research",
        value=auto_title,
        key="rr_topic",
        help="Used as the topic when generating the LinkedIn post. Pre-filled from the first heading.",
    )

    ingest_col, run_col, _ = st.columns([2, 2, 4])

    # ── Ingest only ──────────────────────────────────────────────────────────
    if ingest_col.button("📥 Ingest into KB", key="rr_ingest_btn"):
        run_id = str(uuid.uuid4())
        with st.spinner("Ingesting research report …"):
            ok = ingest_url(
                url=f"manual_research:{run_id}",
                content=rr_raw_text,
                title=topic_input or auto_title or "Research Report",
                category="research_paper",
                ingested_by="manual_research",
                run_id=run_id,
            )
            save_research_output(
                run_id=run_id,
                topic=topic_input or auto_title,
                raw_report=rr_raw_text,
                citations=found_citations,
                ingested=1 if ok else 0,
                skipped=0 if ok else 1,
                failed=0,
                cost_usd=0.0,
            )
        if ok:
            st.success(f"Report ingested into knowledge base (run_id: `{run_id[:8]}…`)")
        else:
            st.info("Already in the knowledge base (duplicate skipped). Research output saved.")
        st.session_state.rr_parsed = {
            "title": topic_input or auto_title,
            "urls": found_urls,
            "text": rr_raw_text,
            "run_id": run_id,
        }
        st.rerun()

    # ── Ingest + Generate post ───────────────────────────────────────────────
    if run_col.button("⚡ Ingest & Generate Post", type="primary", key="rr_run_btn",
                      disabled=not topic_input.strip()):
        run_id = str(uuid.uuid4())
        st.session_state.rr_result = None

        with st.status("Running pipeline from uploaded research …", expanded=True) as pipeline_status:
            # Ingest full report text
            st.write("📥 Ingesting research report …")
            ok = ingest_url(
                url=f"manual_research:{run_id}",
                content=rr_raw_text,
                title=topic_input,
                category="research_paper",
                ingested_by="manual_research",
                run_id=run_id,
            )
            save_research_output(
                run_id=run_id,
                topic=topic_input,
                raw_report=rr_raw_text,
                citations=found_citations,
                ingested=1 if ok else 0,
                skipped=0 if ok else 1,
                failed=0,
                cost_usd=0.0,
            )
            st.write(f"  {'✅ Ingested' if ok else '⏭️ Duplicate — skipped (report already in KB)'}")
            if found_citations:
                st.write(f"  📚 {len(found_citations)} reference(s) saved")

            # Steps 2-5
            st.write("🧠 **Step 2/4** — Analysing insights …")
            try:
                result = run_from_research(
                    topic=topic_input,
                    research_report=rr_raw_text,
                    citations=found_citations,
                    run_id=run_id,
                )
            except Exception as exc:
                pipeline_status.update(label="Pipeline failed", state="error")
                st.error(f"Pipeline error: {exc}")
                st.stop()

            st.write("  ✅ Analysis, fact-check, writing & optimisation complete")
            pipeline_status.update(label="Done! Post saved as draft.", state="complete")
            st.session_state.rr_result = result

        st.rerun()

# Show result after rerun
if st.session_state.rr_result:
    res = st.session_state.rr_result
    st.markdown("---")
    st.subheader("Generated Post")
    st.caption(f"Post ID: `{res['post_id']}` · Run: `{res['run_id'][:8]}…` · Saved as **draft** — approve it in History.")
    st.text_area("Post content (read-only preview)", value=res["final_post"], height=320, key="rr_preview", disabled=True)
    if st.button("🔄 Clear & start over", key="rr_clear"):
        st.session_state.rr_result = None
        st.session_state.rr_parsed = None
        st.rerun()

