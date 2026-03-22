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

You then review the draft in a local Streamlit UI and approve or discard it.

There's also a **Topic Suggestion** system that uses Claude Sonnet to generate 10 fresh topic ideas on demand, saved to a queue so you never run out.

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
| Config | python-dotenv + PyYAML |

---

## Project Structure

```
content-agent/
├── app.py                  # Streamlit entry point
├── pages/                  # UI pages (Generate, History, Knowledge Base, Settings)
├── agents/                 # One agent per file
├── pipeline/               # CrewAI crew + model router
├── rag/                    # Embedder, ChromaDB client, fetcher, ingestor
├── db/                     # SQLite models, queries
├── prompts/                # All LLM prompts as .txt files
├── config/                 # Settings (pydantic) + strategy.yaml
├── scripts/                # Utility scripts (e.g. bulk URL ingestion)
├── data/                   # Local DB + ChromaDB (gitignored)
└── logs/                   # Run logs (gitignored)
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Arian-MU/content-team.git
cd content-team
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Then fill in your four API keys in `.env`:

```
ANTHROPIC_API_KEY=...
PERPLEXITY_API_KEY=...
DEEPSEEK_API_KEY=...
VOYAGE_API_KEY=...
```

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## API Keys Required

| Key | Provider | Used by |
|-----|----------|---------|
| `ANTHROPIC_API_KEY` | [anthropic.com](https://anthropic.com) | Agents 1, 3, 4 + Topic Agent |
| `PERPLEXITY_API_KEY` | [perplexity.ai](https://perplexity.ai) | Agent 0 (Web Researcher) |
| `DEEPSEEK_API_KEY` | [deepseek.com](https://deepseek.com) | Agent 2 (Fact Checker) |
| `VOYAGE_API_KEY` | [voyageai.com](https://voyageai.com) | Embeddings |

API keys are **never** hardcoded. They are loaded exclusively from `.env` via `config/settings.py`.

---

## Target Audience (of the posts generated)

- International students entering the Australian tech job market
- Early-career developers in Australia

Topics focus on: ATS systems, resume strategies, local networking, and visa/work rights.

---

## Development Notes

- See [COPILOT_CONTEXT.md](COPILOT_CONTEXT.md) for the full coding rules and architecture decisions.
- See [TECH_SPEC.md](TECH_SPEC.md) for the complete technical specification.
- See [PRD.md](PRD.md) for the product requirements document.
- See [TASK.md](TASK.md) for the phased build plan.

---

## License

Private — all rights reserved.
