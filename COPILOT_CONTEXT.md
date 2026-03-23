# COPILOT_CONTEXT.md
## AI LinkedIn Content Generation System — v5.0 FINAL LOCKED

Read this before every session. This is the single source of truth.

---

## What This Is

A local multi-agent AI system that generates LinkedIn posts. Python + Streamlit. Runs on the user's machine. User triggers generation, reviews output, approves. Agents do everything in between.

---

## Two Systems

**System A — Topic Suggestion (standalone, on demand)**
User clicks "Refresh Topic Ideas". Topic Agent returns 10 fresh suggestions. Saved to queue.

**System B — Content Pipeline (sequential, per post)**
5 agents run in order. User only touches it at the end to review.

---

## Agent Pipeline — LOCKED

```
Topic input
     ↓
Agent 0  │ Perplexity sonar-deep-research  │ Deep research + fetch + ingest to ChromaDB
     ↓
Agent 1  │ Claude Sonnet                   │ Synthesise research + ChromaDB
     ↓
Agent 2  │ DeepSeek V3                     │ Fact check + validate
     ↓
Agent 3  │ Claude Sonnet                   │ Write post in user's voice
     ↓
Agent 4  │ Claude Sonnet                   │ Optimise hook + readability
     ↓
User review in Streamlit
```

---

## Tech Stack — LOCKED

| Component | Technology |
|---|---|
| Framework | CrewAI Process.sequential |
| UI | Streamlit → localhost:8501 |
| Agent 0 | Perplexity sonar-deep-research (OpenAI-compatible client) |
| Agents 1,3,4 + Topic | Claude Sonnet claude-sonnet-4-5-20251001 |
| Agent 2 | DeepSeek V3 deepseek-chat (OpenAI-compatible client) |
| Embeddings | Voyage AI voyage-3.5 |
| Chunking | LangChain RecursiveCharacterTextSplitter 512t / 20% overlap |
| Vector DB | ChromaDB local |
| PDF extraction | pymupdf4llm → pdfplumber fallback |
| HTML scraping | BeautifulSoup + requests |
| Database | SQLite |
| Config | python-dotenv + PyYAML |

---

## Four API Keys — All Required

```
ANTHROPIC_API_KEY     Claude Sonnet
PERPLEXITY_API_KEY    Sonar Deep Research
DEEPSEEK_API_KEY      DeepSeek V3
VOYAGE_API_KEY        voyage-3.5 embeddings
```

All loaded from .env via config/settings.py. Never hardcoded anywhere.

---

## Non-Negotiable Coding Rules

1. Never hardcode API keys — .env via config/settings.py
2. Never hardcode model names — pipeline/router.py only
3. One agent per file in agents/
4. All prompts in prompts/*.txt — never inline in Python
5. All DB operations in db/queries.py — no raw SQL elsewhere
6. All ChromaDB operations in rag/chromadb_client.py
7. All URL fetching through rag/fetcher.py — never call requests in agents
8. Log every agent run to run_logs table
9. Inject config/strategy.yaml into every agent via build_system_context()
10. MD5 hash check before every ChromaDB ingest
11. Agent 4 failure = silent fallback to Agent 3 output, never abort
12. URL fetch failure = log status, skip, never abort pipeline
13. PDFs are never skipped — always attempt pymupdf4llm then pdfplumber

---

## RAG Rules — KISS

- Chunking: RecursiveCharacterTextSplitter ONLY — 512 tokens, 20% overlap
- No semantic chunking, no hierarchical chunking in v1
- Retrieval: dynamic similarity threshold 0.75, fetch top 20, return only relevant
- Embedding: voyage-3.5 only — switching models requires full re-embed
- Dedup: MD5 hash on full content before every ingest

---

## Key Design Decisions

**Why Perplexity for Agent 0?**
Purpose-built autonomous deep research. Fires 18-28 searches per run. Returns structured citations. ~$0.15/run cheaper than maxing out Claude search.

**Why Voyage 3.5?**
Best text retrieval quality. 200M free tokens. GA stable. 32K context window handles long research papers.

**Why recursive chunking not semantic?**
NAACL 2025 research showed semantic chunking produced 43-token fragments that hurt answer quality. Recursive chunking outperformed it on realistic documents. 80% of the benefit at 20% complexity. Revisit only if retrieval is measurably poor after real usage.

**Why save Agent 0 raw output to SQLite?**
Full audit trail. Every claim in every post traceable to exact research source. Debugging. Reuse for related topics.

**Why dynamic similarity threshold?**
Fixed chunk count is arbitrary. Score-based filtering returns only genuinely relevant content. System improves as ChromaDB grows.

**Why two-layer PDF extraction?**
Research papers are the highest credibility sources. Never skip them. pymupdf4llm is fast and RAG-optimised. pdfplumber handles complex tables better. Two layers = near-zero extraction failures.

**Why DeepSeek for Agent 2?**
Fact checking is pure analytical logic. No creativity, no tool use. 10x cheaper. Equally capable.

---

## Topic Interaction Modes

```
Mode 1: Pick from queue     ← default, 90% of the time
Mode 2: Type custom topic   ← when inspired
Mode 3: Refresh queue       ← weekly, ~2 minutes
```

---

## Fetch Status Types

`success` `paywalled` `dead` `blocked` `timeout` `failed` `duplicate`

Always returns structured dict. Never raises exceptions to pipeline.

---

## Database Tables

- `posts` — generated content + status
- `research_outputs` — Agent 0 raw Perplexity reports + citations (unmodified)
- `topics` — queue with used/unused flag
- `run_logs` — every agent execution, tokens, cost, duration

---

## Session State During Pipeline

```python
st.session_state = {
    "current_topic":       str,
    "run_id":              str,
    "research_report":     str,    # Agent 0 — reused on Regenerate
    "analysis_output":     str,    # Agent 1 — reused on Regenerate
    "validation_output":   str,    # Agent 2 — reused on Regenerate
    "draft_post":          str,    # Agent 3
    "final_post":          str,    # Agent 4 — shown to user
    "sources_used":        list,
    "ingestion_summary":   dict,
    "run_cost_usd":        float,
    "pipeline_complete":   bool
}
```

Regenerate reuses Agent 0-2 outputs. Only reruns Agent 3+4. Cost ~$0.04.
