# Product Requirements Document
## AI LinkedIn Content Generation System

**Version:** 5.0 — FINAL LOCKED  
**Status:** Ready for development  
**Owner:** L  
**Last updated:** March 2026

---

## 1. What This Is

A local AI-powered system that researches, writes, and manages LinkedIn posts for an early-career tech professional targeting the Australian job market.

The user spends 2 minutes per post. The system does everything else.

---

## 2. Goals

- Generate high-quality, credible LinkedIn posts grounded in real deep research
- Keep content on-strategy automatically — right audience, right voice, every time
- Never run out of topic ideas
- Passively grow a knowledge base with every post generated
- Cost under $20 AUD/month at 15 posts/month
- Run fully local — no cloud hosting beyond API calls
- Keep the codebase simple, maintainable, and easy to debug

---

## 3. Non-Goals (v1)

- Auto-publishing to LinkedIn
- Multi-user support
- Mobile interface
- Semantic or hierarchical chunking (revisit only if retrieval quality is measurably poor after real usage)
- Gemini Embedding 2 (revisit when out of Preview)

---

## 4. Target Audience (of posts being generated)

**Primary:** International students entering the Australian tech job market
**Secondary:** Early-career developers in Australia

**Pain points:**
- Don't understand ATS systems
- Resume not getting responses
- No local professional network
- Uncertainty around work rights and visa conditions

---

## 5. Final Agent Architecture — LOCKED

### 5.1 The Two Systems

```
SYSTEM A — Topic Suggestion (standalone, on demand)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Topic Agent → suggests 10 topics → saved to SQLite queue

SYSTEM B — Content Pipeline (sequential, per post)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent 0 → Agent 1 → Agent 2 → Agent 3 → Agent 4 → User Review
```

### 5.2 Final Model Assignment — LOCKED

| Agent | Name | Model | Provider | Role |
|---|---|---|---|---|
| Topic Agent | Topic Suggester | Claude Sonnet | Anthropic | Suggests 10 fresh topics based on trends + post history |
| Agent 0 | Web Researcher | sonar-deep-research | Perplexity | Deep web research, fetches + ingests all citations |
| Agent 1 | Research Analyst | Claude Sonnet | Anthropic | Synthesises Agent 0 + ChromaDB into insights |
| Agent 2 | Fact Checker | DeepSeek V3 | DeepSeek | Validates claims, flags weak points |
| Agent 3 | Content Writer | Claude Sonnet | Anthropic | Writes post in user's voice |
| Agent 4 | Optimiser | Claude Sonnet | Anthropic | Strengthens hook, improves readability |

### 5.3 Why Each Model

- **Perplexity Sonar Deep Research** — autonomous 18-28 searches per run, structured citations, ~$0.15/run
- **Claude Sonnet** — best writing quality, consistent reasoning
- **DeepSeek V3** — fact checking is pure logic, 10x cheaper, equally capable
- **Four API keys total:** Anthropic + Perplexity + DeepSeek + Voyage

---

## 6. RAG Stack — LOCKED (KISS)

### Embedding: Voyage 3.5
- Best retrieval quality for text RAG
- 200M free tokens before any cost
- GA and stable
- 32K context window

### Chunking: Recursive — 512 tokens, 20% overlap
- Simple, well-understood, battle-tested
- 80% of the benefit at 20% of the complexity
- Overlap preserves context across chunk boundaries
- No tuning required

**Why not semantic/hierarchical chunking?**
Peer-reviewed NAACL 2025 research found semantic chunking produced 43-token fragments that hurt answer quality despite good retrieval recall. Recursive chunking outperformed it on realistic document sets. Revisit only if retrieval quality is measurably poor after real usage.

### Retrieval: Dynamic similarity threshold
- Score threshold 0.75 — quality controlled, not count controlled
- Fetch top 20 candidates, return only genuinely relevant ones
- System gets smarter as ChromaDB grows

### PDF Handling: Two-layer extraction
- Layer 1: pymupdf4llm — fast, RAG-optimised markdown
- Layer 2: pdfplumber fallback — better for tables
- PDFs are never skipped — research papers are gold

---

## 7. Strategy Configuration (One-Time Setup)

```yaml
# config/strategy.yaml
author:
  name: ""
  role: ""
  location: "Australia"

target_audience:
  primary: ""
  secondary: ""
  pain_points: []

content:
  topics: []
  avoid: []

voice:
  tone: ""
  style: ""
  avoid: ""
  sample_posts: []

research:
  trusted_source_types:
    - "Peer-reviewed research"
    - "Government data (abs.gov.au, dewr.gov.au)"
    - "LinkedIn official reports"
    - "SEEK market insights"
    - "Recognised universities"
  auto_ingest: true
```

Filled in once via Settings page. Injected into every agent automatically.

---

## 8. Complete User Workflow

### 8.1 First Time Setup (once — ~10 minutes)
```
Open localhost:8501
→ Redirected to Settings page
→ Fill in strategy form
→ Click Save
→ config/strategy.yaml written to disk
→ Never touch again unless strategy changes
```

---

### 8.2 Weekly — Refresh Topic Ideas (~2 minutes)
```
Click "Refresh Topic Ideas" in sidebar
→ Topic Agent runs
→ Checks post history (avoids repeats)
→ Searches trending niche topics
→ Returns 10 suggestions: title | why | source URL
→ Tick favourites → Save to Queue
→ Queue ready for the week ahead
```

---

### 8.3 Daily — Generate a Post (~2 minutes total)

#### Choose your topic (3 modes)
```
Mode 1 — Pick from queue (default, 90% of the time)
  Queue topic buttons shown prominently
  Click one that feels right today

Mode 2 — Type custom topic (when inspired)
  Free text input always visible below queue
  Type directly → bypasses queue

Mode 3 — Weekly refresh (Sunday ~2 minutes)
  Covered in 8.2 above
```

#### Pipeline runs — what happens inside
```
YOU click Generate
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT 0 — Perplexity Sonar Deep Research                │
│                                                         │
│ 1. Fires 18-28 autonomous web searches                  │
│    Searches structured by strategy context:             │
│    "[topic] Australia 2026"                             │
│    "[topic] research data statistics"                   │
│    "[topic] international students"                     │
│    "[topic] site:abs.gov.au OR seek.com.au"             │
│    ...and more based on topic                           │
│                                                         │
│ 2. Returns full markdown research report                │
│    + numbered citation URLs                             │
│                                                         │
│ 3. Saves raw report to SQLite (unmodified)              │
│    Full audit trail — every claim traceable             │
│                                                         │
│ 4. Fetches every citation URL:                          │
│    HEAD check → is it alive?                            │
│    PDF? → pymupdf4llm → pdfplumber fallback             │
│    HTML? → paywall check → content extract              │
│    Result: success | paywalled | dead | blocked         │
│                                                         │
│ 5. Ingests every successful fetch into ChromaDB         │
│    Recursive chunking: 512 tokens, 20% overlap          │
│    Voyage 3.5 embedding                                 │
│    MD5 dedup — never double-ingests                     │
│                                                         │
│ Streamlit shows:                                        │
│  ✅ Ingested: 7 (4 HTML + 3 PDFs)                       │
│  🔒 Paywalled: 2                                        │
│  💀 Dead: 1   ⚠️ Failed: 1                              │
│  Knowledge base: 847 → 863 docs                         │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT 1 — Claude Sonnet (Research Analyst)              │
│                                                         │
│ 1. Receives Agent 0 full research report                │
│ 2. Queries ChromaDB:                                    │
│    → similarity search, score threshold 0.75            │
│    → fetches top 20 candidates                          │
│    → returns only genuinely relevant chunks             │
│    → could be 3 chunks (early) or 15 (after months)    │
│ 3. Combines web report + ChromaDB context               │
│ 4. Outputs structured insights + content angles         │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT 2 — DeepSeek V3 (Fact Checker)                    │
│                                                         │
│ 1. Receives Agent 1 insights                            │
│ 2. Validates every claim against Agent 0 citations      │
│ 3. Weak claims → "research suggests..."                 │
│    Unverifiable claims → removed                        │
│ 4. Nothing ungrounded passes through                    │
│ 5. Outputs: clean validated insights                    │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT 3 — Claude Sonnet (Content Writer)                │
│                                                         │
│ 1. Receives validated insights                          │
│ 2. Loads your voice samples from strategy.yaml          │
│ 3. Writes post in YOUR voice for YOUR audience          │
│ 4. Follows format:                                      │
│    Hook (1-2 lines, scroll-stopping)                    │
│    Observation (2-3 lines)                              │
│    Insight backed by research (3-4 lines)               │
│    Practical takeaway (2-3 lines)                       │
│    Soft CTA (1 line)                                    │
│    3-5 hashtags                                         │
│ 5. 150-250 words                                        │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT 4 — Claude Sonnet (Optimiser)                     │
│                                                         │
│ 1. Receives draft post                                  │
│ 2. Strengthens hook                                     │
│ 3. Improves readability                                 │
│ 4. Does NOT add new claims                              │
│ 5. Does NOT change meaning                              │
│ 6. If fails → silently returns Agent 3 output           │
└─────────────────────────────────────────────────────────┘
        │
        ▼
YOU review in Streamlit
  - Final post in editable text area
  - Expandable: Ingestion summary
  - Expandable: Sources used (citation URLs)
  - Expandable: Research report (Agent 0 raw)
  - Expandable: Validated insights (Agent 2)
  - Estimated cost: ~$0.32 USD
        │
   ┌────┴──────────────────────────────┐
   │                                   │
Approve              Regenerate (reruns Agent 3+4 only)
   │                 Cost: ~$0.04      │
   │                                   │
Save to SQLite              New post shown
Copy block shown
   │
(Optional) Export to Google Drive
```

---

### 8.4 View Post History
```
History page
→ Filter: All / Approved / Edited / Published
→ Table: Date | Topic | Status | Preview
→ Click row → full post expands
→ Mark Published | Copy | Delete
```

---

### 8.5 Manage Knowledge Base
```
Knowledge Base page
→ 3 metric cards: Articles | LinkedIn Posts | Research Papers
→ Manual URL + category + Add (single)
→ Batch .txt upload with progress bar
→ Note: Agent 0 auto-grows this every single run
```

---

## 9. Compounding Knowledge Effect

```
Month 1:  15 posts → ~75-100 new documents ingested
Month 2:  +75-100 more documents
Month 3:  ChromaDB has 200-300 deep-researched sources
          Agent 1 ChromaDB queries return richer context
          Posts become more specific and credible over time
Month 6+: Knowledge base covers your entire niche deeply
          System is meaningfully smarter than day one
```

This happens automatically. You never manually add anything.

---

## 10. Final Cost at 15 Posts/Month

| Item | USD | AUD |
|---|---|---|
| 15 × Agent 0 Perplexity | $2.25 | ~$3.19 |
| 15 × Agents 1-4 Claude | $1.80 | ~$2.55 |
| 4 × Topic suggestion runs | $0.40 | ~$0.57 |
| Voyage 3.5 embeddings | $0.00 (200M free) | $0.00 |
| **Monthly total** | **~$4.45** | **~$6.31** |
| Your budget | $14.00 | $20.00 |
| **Remaining headroom** | **~$9.55** | **~$13.69** |

---

## 11. Future Upgrade Path (not v1)

| Upgrade | When to consider |
|---|---|
| Semantic / hierarchical chunking | If retrieval quality measurably poor after 3 months real usage |
| Gemini Embedding 2 | When out of Preview + 6-page PDF limit resolved |
| PDF table extraction improvements | If research papers with heavy tables give poor results |
| Google Drive auto-sync | When post volume makes manual management tedious |

---

## 12. Success Metrics

- 15 posts generated per month
- Under 2 minutes user review time per post
- Zero fabricated statistics in approved posts
- ~78% citation fetch success rate
- ChromaDB grows every run
- Topic queue never empty
- Cost under $8 AUD/month
