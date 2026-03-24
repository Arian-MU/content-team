# TASK.md
## AI LinkedIn Content Generation System — v5.0 FINAL LOCKED

Read COPILOT_CONTEXT.md and TECH_SPEC.md before starting any phase.
Complete and test each phase before moving to the next. No exceptions.

---

## Phase 1 — Scaffold + Config

- [ ] Create full folder structure per TECH_SPEC.md section 2
- [ ] Create `requirements.txt` per TECH_SPEC.md section 12
- [ ] Create `.env.example` with all 4 API keys + all variable names, no values
- [ ] Create `config/strategy.yaml` empty template with all fields
- [ ] Create `config/settings.py` — pydantic-settings, typed Settings object, loads all env vars
- [ ] Create `pipeline/router.py` — AGENT_MODELS dict + get_model(agent_name) function
- [ ] Smoke test: `python -c "from config.settings import settings; print('OK')"`

---

## Phase 2 — Database Layer

- [ ] Create `db/database.py` — SQLite connection + init_db() creates all 4 tables
- [ ] Create `db/models.py` — Post, ResearchOutput, Topic, RunLog dataclasses
- [ ] Create `db/queries.py` with all CRUD:
  - `save_post(topic, content_en, model_writer, model_optimiser, run_id, status) -> int`
  - `update_post_status(post_id, status)`
  - `get_posts(status=None) -> list[Post]`
  - `delete_post(post_id)`
  - `save_research_output(run_id, topic, raw_report, citations, ingested, skipped, failed, cost_usd)`
  - `get_research_output(run_id) -> ResearchOutput`
  - `add_topic(topic, source, source_url=None) -> int`
  - `get_unused_topics(limit=5) -> list[Topic]`
  - `mark_topic_used(topic_id)`
  - `save_run_log(run_id, agent, input, output, model, tokens_in, tokens_out, cost_usd, duration_ms)`
- [ ] Smoke test: init_db(), insert one of each type, query back, verify schema

---

## Phase 3 — RAG Layer

### 3a — Embedder (Voyage 3.5)
- [ ] Create `rag/embedder.py`:
  - Voyage AI client singleton (lazy init)
  - `embed(texts: list[str]) -> list[list[float]]`
  - `embed_single(text: str) -> list[float]`
  - Batch support for efficient ingestion

### 3b — ChromaDB Client
- [ ] Create `rag/chromadb_client.py`:
  - `get_collection()` — get or create linkedin_knowledge
  - `query(text, score_threshold=0.75, category=None) -> list[dict]`
    - Fetch top 20 candidates
    - Filter by similarity score — never fixed count
    - Return content + source_url + category + similarity
  - `get_doc_count(category=None) -> int`
  - `document_exists(content_hash: str) -> bool`

### 3c — Fetcher (HTML + PDF)
- [ ] Create `rag/fetcher.py`:
  - `fetch_article(url: str) -> dict` — master function
  - HEAD check first (5s timeout)
  - PDF detection: content-type header OR .pdf extension
  - `_fetch_pdf(url, result)`:
    - Layer 1: pymupdf4llm markdown extraction
    - Layer 2: pdfplumber fallback
    - Never skips PDFs
  - `_fetch_html(url, result)`:
    - Paywall signal detection
    - BeautifulSoup noise removal + extraction
    - Min 300 chars content check
  - 1 second polite delay per fetch
  - Always returns structured dict, never raises to caller
  - Status values: success | paywalled | dead | blocked | timeout | failed

### 3d — Ingestor
- [ ] Create `rag/ingestor.py`:
  - `ingest_url(url, content, title, category, ingested_by, run_id) -> bool`
  - MD5 hash dedup via chromadb_client.document_exists()
  - `chunk_text(text) -> list[str]`:
    - LangChain RecursiveCharacterTextSplitter
    - chunk_size=512, chunk_overlap=102 (20%)
    - separators=["\n\n", "\n", ". ", " ", ""]
  - Batch embed all chunks via embedder.embed()
  - Store in ChromaDB with full metadata
  - Returns True if ingested, False if duplicate

### 3e — Scripts
- [ ] Create `scripts/ingest_urls.py` — reads urls_to_ingest.txt, category per line
- [ ] Smoke test:
  - Fetch 1 HTML article (verify success)
  - Fetch 1 PDF research paper (verify both layers tried)
  - Ingest both, query a topic, verify results returned
  - Re-ingest same URL, verify dedup returns False

---

## Phase 4 — Prompts

All in `prompts/*.txt`. Loaded from file in agents. Never written inline.

- [ ] `prompts/topic_agent.txt`:
  - Role: content strategist, early-career tech Australia
  - Injected context: strategy + post history list
  - Task: 10 fresh topics not already in post history
  - Output: numbered list — topic | why relevant now | source URL

- [ ] `prompts/researcher.txt`:
  - Role: deep research analyst
  - Injected context: strategy (trusted source types)
  - Task: find credible, current, authoritative sources
  - Output: structured markdown report with numbered citations

- [ ] `prompts/analyst.txt`:
  - Role: research synthesis analyst
  - Injected context: Agent 0 report + ChromaDB chunks
  - Task: extract insights, evidence, content angles
  - Output: structured bullet points

- [ ] `prompts/fact_checker.txt`:
  - Role: fact checker
  - Rules: no fabricated stats, rephrase uncertain as "research suggests..."
  - Output: validated insights with [FLAG] on softened claims

- [ ] `prompts/writer.txt`:
  - Role: LinkedIn content writer, early-career tech, Australia
  - Injected context: validated insights + voice samples from strategy.yaml
  - Format: Hook → Observation → Insight → Takeaway → CTA → Hashtags
  - Length: 150-250 words, conversational, first-person

- [ ] `prompts/optimiser.txt`:
  - Role: LinkedIn optimiser
  - Task: improve hook + readability only
  - Hard rule: no new claims, no meaning changes
  - Output: improved post only, no explanation

---

## Phase 5 — Agent Layer

- [ ] `agents/topic_agent.py`:
  - Claude Sonnet
  - Loads strategy.yaml
  - Fetches post history from SQLite as context
  - Returns list of 10 topic dicts

- [ ] `agents/researcher_agent.py`:
  - Perplexity via OpenAI client (base_url: https://api.perplexity.ai)
  - model: sonar-deep-research
  - Saves raw response to research_outputs table
  - Calls fetcher.fetch_article() for every citation
  - Calls ingestor.ingest_url() for every success
  - Returns: research_report + citations + ingestion_summary

- [ ] `agents/analyst_agent.py`:
  - Claude Sonnet
  - Receives Agent 0 research report
  - Calls chromadb_client.query() dynamic threshold
  - Combines both into structured insights

- [ ] `agents/fact_checker_agent.py`:
  - DeepSeek V3 via OpenAI client
  - Validates against Agent 0 citations
  - Returns clean validated insights

- [ ] `agents/writer_agent.py`:
  - Claude Sonnet
  - Loads voice samples from strategy.yaml
  - Writes post per format in writer prompt

- [ ] `agents/optimiser_agent.py`:
  - Claude Sonnet
  - try/except — silent fallback to writer output
  - Never aborts pipeline

---

## Phase 6 — Pipeline Orchestration

- [ ] Create `pipeline/crew.py`:
  - CrewAI Crew with Process.sequential
  - `run_pipeline(topic: str, resume_from: str = None) -> dict`
  - resume_from="writer" → skips Agent 0-2, reuses session_state
  - Tracks tokens + cost per agent
  - Logs all agents to run_logs
  - Returns: run_id | research | analysis | validation | draft | final | sources | ingestion_summary | cost_usd
- [ ] Smoke test:
  - Full pipeline on "ATS tips international students Australia"
  - Verify research saved to SQLite
  - Verify citations ingested to ChromaDB
  - Print final post + total cost

---

## Phase 7 — Streamlit UI

- [ ] `app.py`:
  - init_db() on startup
  - Load strategy.yaml — if missing, redirect to Settings
  - Sidebar: "Refresh Topic Ideas" button + page links

- [ ] `pages/4_Settings.py`:
  - Form for all strategy.yaml fields
  - sample_posts as multiline textarea
  - Save → writes strategy.yaml
  - Pre-populates if file exists

- [ ] `pages/1_Generate.py`:
  - Up to 5 queue topic buttons (prominent)
  - Custom topic text input (always visible below)
  - Generate → progress bar with per-agent status
  - After Agent 0: ingestion summary card
  - Final post in editable st.text_area
  - Expandables: Ingestion Summary | Sources | Research Report | Validated Insights
  - Estimated cost display
  - Approve | Regenerate | Edit & Approve | Discard
  - st.code clipboard block on approve

- [ ] `pages/2_History.py`:
  - Filter: All / Approved / Edited / Published
  - st.dataframe: Date | Topic | Status | Preview
  - Row click → full post + Mark Published | Copy | Delete

- [ ] `pages/3_Knowledge_Base.py`:
  - 3 metric cards per category
  - Single URL + category + Add
  - Batch .txt uploader + st.progress
  - Per-URL result shown

---

## Phase 8 — Topic Suggestion Agent

- [ ] Wire sidebar button to topic_agent.py
- [ ] 10 result cards: title | why | source | checkbox
- [ ] Save Selected → add_topic() per checked
- [ ] st.success with saved count

---

## Phase 9 — Optional: Google Drive Sync

- [ ] README: Drive API setup steps
- [ ] `db/gdrive_sync.py`: is_gdrive_enabled() + export_post_to_drive(post_id)
- [ ] Hook into approve flow

---

## Phase 10 — README + Polish

- [ ] README: overview, prerequisites, 4 API key setup, install, run, cost
- [ ] Makefile: `make install` `make run` `make ingest`
- [ ] Test all prompts on 5 real topics
- [ ] PDF test: verify 3 real research paper URLs ingest correctly
- [ ] End-to-end: 3 posts generated, approved, history verified, cost logged
- [ ] Confirm ChromaDB grows after each run

---

## Future UX Improvements (Post Phase 10)

### Two-Phase Generate Flow
Currently the Generate page runs all 5 pipeline steps automatically without
stopping. A two-phase flow would significantly improve UX and reduce wasted
cost on bad research runs:

- **Phase 1 (Research):** Run Researcher agent only → show user the research
  report, citation list, and ingestion summary → present a
  **"Looks good — continue →"** button and a **"Discard"** button
- **Phase 2 (Write):** On confirmation, run Analyst → Fact-checker → Writer →
  Optimiser and produce the final post

Benefits:
- User can validate source quality before the expensive writing steps run
- If research is poor, user discards early and saves ~$0.28 per run
- Gives user agency over what goes into the final post

Implementation: store `gen_research` in `st.session_state` after Phase 1,
render a confirmation button, then run the remaining agents only when confirmed.
No pipeline/crew.py changes needed — split the existing Generate page logic
into two button-triggered blocks.

---

## Copilot Rules — Enforced Every Session

- Read COPILOT_CONTEXT.md before starting
- Never SQL outside db/queries.py
- Never ChromaDB outside rag/chromadb_client.py
- Never fetch URLs outside rag/fetcher.py
- Never hardcode model names — pipeline/router.py
- Never write prompts inline — prompts/*.txt
- PDFs are never skipped — both layers always attempted
- Chunking is RecursiveCharacterTextSplitter only — no semantic, no hierarchical
- Test each phase before moving to the next
