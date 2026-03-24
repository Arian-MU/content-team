from __future__ import annotations

import uuid

import streamlit as st

from rag.chromadb_client import get_doc_count
from rag.fetcher import fetch_article
from rag.ingestor import ingest_url

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

