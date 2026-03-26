# Content Team — AI LinkedIn Content Generation System

> A local multi-agent AI pipeline that researches, writes, and manages LinkedIn posts — so you spend 2 minutes per post, not 2 hours.

---

## What It Does

You pick a topic. Five AI agents handle everything else:

| Step | Agent | Model | Role |
|------|-------|-------|------|
| 0 | Web Researcher | Perplexity sonar-deep-research | Deep research + fetch + save to knowledge base |
| 1 | Research Analyst | Claude Sonnet | Synthesise research into key insights |
| 2 | Fact Checker | DeepSeek V3 | Validate claims, flag weak points |
| 3 | Content Writer | Claude Sonnet | Write post in your voice |
| 4 | Optimiser | Claude Sonnet | Sharpen the hook, improve readability |

You then review the draft in a local Streamlit UI — approve, edit, or discard.

There's also a **Topic Suggestion** system (Claude Sonnet) that generates 10 fresh ideas on demand, saved to a queue so you never run out.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent framework | CrewAI (sequential pipeline) |
| UI | Streamlit → `localhost:8501` |
| Research | Perplexity sonar-deep-research |
| Primary LLM | Claude Sonnet (`claude-sonnet-4-5-20251001`) |
| Validation LLM | DeepSeek V3 (`deepseek-chat`) |
| Embeddings | Voyage AI `voyage-3.5` |
| Vector DB | ChromaDB (local, persistent) |
| App DB | SQLite |
| PDF extraction | pymupdf4llm → pdfplumber fallback |
| HTML scraping | BeautifulSoup + requests |
| Config | pydantic-settings + PyYAML |

---

## Project Structure

```
content-agent/
├── app.py                  # Streamlit entry point
├── pages/                  # UI pages (Generate, History, Knowledge Base, Settings)
├── agents/                 # One agent per file
├── pipeline/               # CrewAI crew + model router
├── rag/                    # Embedder, ChromaDB client, fetcher, ingestor
├── db/                     # SQLite models, queries, Google Drive sync
├── prompts/                # All LLM prompts as .txt files
├── config/                 # Settings (pydantic) + strategy.yaml
├── scripts/                # Utility scripts (bulk URL ingestion)
├── data/                   # Local DB + ChromaDB (gitignored)
└── logs/                   # Run logs (gitignored)
```

---

## Setup

### Prerequisites

- Python 3.12 (3.13+ not fully supported by all dependencies)
- API keys for Anthropic, Perplexity, DeepSeek, and Voyage AI (see below)

### 1. Clone the repo

```bash
git clone https://github.com/Arian-MU/content-team.git
cd content-team
```

### 2. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
make install
# or: pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Fill in your four API keys in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
PERPLEXITY_API_KEY=pplx-...
DEEPSEEK_API_KEY=sk-...
VOYAGE_API_KEY=pa-...
```

### 5. Run the app

```bash
make run
# or: streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## API Keys Required

| Key | Provider | Used by |
|-----|----------|---------|
| `ANTHROPIC_API_KEY` | [anthropic.com](https://anthropic.com) | Agents 1, 3, 4 + Topic Agent |
| `PERPLEXITY_API_KEY` | [perplexity.ai](https://perplexity.ai) | Agent 0 (Web Researcher) |
| `DEEPSEEK_API_KEY` | [deepseek.com](https://deepseek.com) | Agent 2 (Fact Checker) |
| `VOYAGE_API_KEY` | [voyageai.com](https://voyageai.com) | Embeddings (Voyage AI) |

API keys are **never** hardcoded. They are loaded exclusively from `.env` via `config/settings.py`.

---

## Knowledge Base (Optional)

You can pre-seed ChromaDB with your own articles, blog posts, and PDFs before running the pipeline. The researcher will automatically retrieve relevant chunks to ground its output.

```bash
# Add URLs (one per line) to data/urls_to_ingest.txt, then:
make ingest

# Or with options:
python scripts/ingest_urls.py --category research --dry-run
```

PDFs are ingested via the **Knowledge Base** page in the UI (drag-and-drop upload).

---

## Google Drive Sync (Optional)

Approved posts can be automatically exported to a Google Drive folder as `.txt` files. To enable:

1. Create a Google Cloud project and enable the **Google Drive API**
2. Create an **OAuth 2.0 Desktop App** credential → download the JSON → save as `config/gdrive_credentials.json`
3. Create a Drive folder and copy its ID from the URL
4. Add to `.env`:
   ```
   GDRIVE_ENABLED=true
   GDRIVE_FOLDER_ID=<your-folder-id>
   ```
5. On first sync, a browser window opens for OAuth consent — the token is saved automatically to `config/gdrive_token.json`

Both `config/gdrive_credentials.json` and `config/gdrive_token.json` are gitignored and will never be committed.

---

## Approximate Running Costs

Each post generation run makes calls to three paid APIs:

| API | Model | Typical cost per run |
|-----|-------|----------------------|
| Perplexity | sonar-deep-research | ~$0.005 |
| Anthropic | Claude Sonnet | ~$0.01–0.03 |
| DeepSeek | deepseek-chat | ~$0.001 |

**Voyage AI** offers 200M free embedding tokens — more than enough for normal use.  
Total: roughly **$0.02–0.05 per post** at current API pricing.

---

## Target Audience (of the posts generated)

- International students entering the Australian tech job market
- Early-career developers in Australia

Topics focus on: ATS systems, resume strategies, local networking, and visa/work rights.

---

## License

Private — all rights reserved.

