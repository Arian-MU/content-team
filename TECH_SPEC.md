# Technical Specification
## AI LinkedIn Content Generation System

**Version:** 5.0 — FINAL LOCKED  
**Stack:** Python + CrewAI + Streamlit + ChromaDB + SQLite

---

## 1. Tech Stack — LOCKED

| Layer | Technology | Provider | Reason |
|---|---|---|---|
| Agent framework | CrewAI | — | Sequential, minimal boilerplate |
| UI | Streamlit | — | Python-native, local, zero HTML/CSS |
| Research LLM | sonar-deep-research | Perplexity | Autonomous deep research, structured citations |
| Primary LLM | claude-sonnet-4-5-20251001 | Anthropic | Best writing + reasoning |
| Validation LLM | deepseek-chat | DeepSeek | Pure logic, 10x cheaper |
| Embedding | voyage-3.5 | Voyage AI | Best text retrieval, 200M free tokens |
| Chunking | RecursiveCharacterTextSplitter | LangChain | KISS — 512 tokens, 20% overlap |
| Vector DB | ChromaDB | — | Local persistent |
| PDF layer 1 | pymupdf4llm | — | RAG-optimised markdown extraction |
| PDF layer 2 | pdfplumber | — | Fallback for tables + complex layouts |
| HTML scraping | BeautifulSoup + requests | — | Content extraction |
| App DB | SQLite | — | Zero setup, personal scale |
| Config | python-dotenv + PyYAML | — | Standard |

---

## 2. Project Structure

```
content-agent/
├── .env
├── .env.example
├── requirements.txt
├── README.md
├── Makefile
├── TASK.md
├── COPILOT_CONTEXT.md
│
├── app.py                        # Streamlit entry point
├── pages/
│   ├── 1_Generate.py
│   ├── 2_History.py
│   ├── 3_Knowledge_Base.py
│   └── 4_Settings.py
│
├── agents/
│   ├── __init__.py
│   ├── topic_agent.py
│   ├── researcher_agent.py       # Agent 0: Perplexity
│   ├── analyst_agent.py          # Agent 1: Claude Sonnet
│   ├── fact_checker_agent.py     # Agent 2: DeepSeek V3
│   ├── writer_agent.py           # Agent 3: Claude Sonnet
│   └── optimiser_agent.py        # Agent 4: Claude Sonnet
│
├── pipeline/
│   ├── __init__.py
│   ├── crew.py
│   └── router.py
│
├── rag/
│   ├── __init__.py
│   ├── chromadb_client.py
│   ├── embedder.py               # Voyage 3.5
│   ├── fetcher.py                # HTML + PDF, all status handling
│   └── ingestor.py               # Recursive chunking + embed + store
│
├── db/
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   └── queries.py
│
├── prompts/
│   ├── topic_agent.txt
│   ├── researcher.txt
│   ├── analyst.txt
│   ├── fact_checker.txt
│   ├── writer.txt
│   └── optimiser.txt
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── strategy.yaml
│
├── scripts/
│   └── ingest_urls.py
│
├── data/
│   ├── chromadb/
│   ├── content_agent.db
│   └── urls_to_ingest.txt
│
└── logs/
    └── run_logs/
```

---

## 3. Model Router — LOCKED

```python
# pipeline/router.py

PERPLEXITY_DEEP_RESEARCH = "sonar-deep-research"
CLAUDE_SONNET             = "claude-sonnet-4-5-20251001"
DEEPSEEK_V3               = "deepseek-chat"

AGENT_MODELS = {
    "topic_agent":   CLAUDE_SONNET,
    "researcher":    PERPLEXITY_DEEP_RESEARCH,
    "analyst":       CLAUDE_SONNET,
    "fact_checker":  DEEPSEEK_V3,
    "writer":        CLAUDE_SONNET,
    "optimiser":     CLAUDE_SONNET,
}

def get_model(agent_name: str) -> str:
    return AGENT_MODELS[agent_name]
```

---

## 4. RAG Implementation — LOCKED (KISS)

### 4.1 Embedder

```python
# rag/embedder.py
import voyageai

_client = None

def get_client():
    global _client
    if not _client:
        _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    return _client

def embed(texts: list[str]) -> list[list[float]]:
    result = get_client().embed(texts, model="voyage-3.5")
    return result.embeddings

def embed_single(text: str) -> list[float]:
    return embed([text])[0]
```

### 4.2 Chunking — Recursive, KISS

```python
# rag/ingestor.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=102,      # 20% overlap
    separators=["\n\n", "\n", ". ", " ", ""]
)

def chunk_text(text: str) -> list[str]:
    return splitter.split_text(text)
```

Simple. No tuning. Battle-tested. Gets you 80% of the benefit immediately.

### 4.3 ChromaDB — Dynamic Similarity Query

```python
# rag/chromadb_client.py

def query(text: str, score_threshold: float = 0.75, category: str = None) -> list[dict]:
    query_embedding = embedder.embed_single(text)
    where = {"category": category} if category else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=20,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    filtered = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        similarity = 1 - distance
        if similarity >= score_threshold:
            filtered.append({
                "content":    doc,
                "source_url": meta.get("source_url"),
                "category":   meta.get("category"),
                "similarity":  round(similarity, 3)
            })

    return filtered   # variable count — quality controlled
```

### 4.4 Ingestor

```python
# rag/ingestor.py

import hashlib
import json

def ingest_url(url: str, content: str, title: str,
               category: str, ingested_by: str, run_id: str) -> bool:

    # Dedup check
    content_hash = hashlib.md5(content.encode()).hexdigest()
    if chromadb_client.document_exists(content_hash):
        return False   # already ingested

    # Chunk
    chunks = chunk_text(content)
    if not chunks:
        return False

    # Embed all chunks in one batch call
    embeddings = embedder.embed(chunks)

    # Build metadata for each chunk
    metadatas = [{
        "source_url":   url,
        "title":        title,
        "category":     category,
        "content_hash": content_hash,
        "ingested_by":  ingested_by,
        "run_id":       run_id,
        "ingested_at":  datetime.utcnow().isoformat(),
        "chunk_index":  i
    } for i, _ in enumerate(chunks)]

    # Store
    collection = chromadb_client.get_collection()
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=[f"{content_hash}_{i}" for i in range(len(chunks))]
    )

    return True
```

---

## 5. Fetcher — LOCKED

```python
# rag/fetcher.py
# Full implementation — see TECH_SPEC v4 section 5 for complete code
# Key behaviours:
#   - HEAD check first (fast, cheap)
#   - PDF detected by content-type or .pdf extension
#   - PDF: pymupdf4llm → pdfplumber fallback
#   - HTML: paywall detection → BeautifulSoup extraction
#   - 1 second polite delay between fetches
#   - Always returns structured dict, never raises to caller
#   - Status: success | paywalled | dead | blocked | timeout | failed

STATUS_TYPES = ["success", "paywalled", "dead", "blocked", "timeout", "failed"]
```

---

## 6. Agent 0 Flow

```python
# agents/researcher_agent.py

def run(topic: str, run_id: str, strategy_context: str) -> dict:

    # 1 — Perplexity deep research
    response = perplexity_client.chat.completions.create(
        model=PERPLEXITY_DEEP_RESEARCH,
        messages=[
            {"role": "system", "content": strategy_context},
            {"role": "user",   "content": f"Deep research: {topic}"}
        ]
    )

    raw_report = response.choices[0].message.content
    citations  = getattr(response, "citations", [])

    # 2 — Save raw to SQLite (unmodified)
    save_research_output(run_id, topic, raw_report, citations)

    # 3 — Fetch + ingest every citation
    summary = {s: [] for s in STATUS_TYPES}

    for url in citations:
        fetch_result = fetcher.fetch_article(url)
        status = fetch_result["status"]

        if status == "success":
            ingested = ingestor.ingest_url(
                url=url,
                content=fetch_result["content"],
                title=fetch_result["title"],
                category="article",
                ingested_by="agent_0",
                run_id=run_id
            )
            if ingested:
                summary["success"].append(url)
        else:
            summary[status].append({"url": url, "reason": fetch_result["reason"]})

    # 4 — Return to Agent 1
    return {
        "research_report":  raw_report,
        "citations":         citations,
        "ingestion_summary": summary
    }
```

---

## 7. Database Schema — LOCKED

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    content_en TEXT NOT NULL,
    model_writer TEXT,
    model_optimiser TEXT,
    status TEXT DEFAULT 'approved',
    run_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

CREATE TABLE research_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    raw_report TEXT NOT NULL,
    citations TEXT NOT NULL,
    ingested_count INTEGER,
    skipped_count INTEGER,
    failed_count INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    source TEXT DEFAULT 'manual',
    source_url TEXT,
    used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    input TEXT,
    output TEXT,
    model TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. Environment Variables — LOCKED

```bash
ANTHROPIC_API_KEY=sk-ant-...
PERPLEXITY_API_KEY=pplx-...
DEEPSEEK_API_KEY=sk-...
VOYAGE_API_KEY=pa-...

CHROMA_PERSIST_DIR=./data/chromadb
CHROMA_COLLECTION_NAME=linkedin_knowledge
SQLITE_DB_PATH=./data/content_agent.db

GDRIVE_ENABLED=false
GDRIVE_FOLDER_ID=
GDRIVE_CREDENTIALS_PATH=./config/gdrive_credentials.json

LOG_LEVEL=INFO
MAX_RETRIES=1
```

---

## 9. Cost Per Post

| Agent | Model | Est. cost |
|---|---|---|
| Agent 0 | Perplexity Deep Research | ~$0.150 |
| Agent 1 | Claude Sonnet | ~$0.048 |
| Agent 2 | DeepSeek V3 | ~$0.003 |
| Agent 3 | Claude Sonnet | ~$0.027 |
| Agent 4 | Claude Sonnet | ~$0.024 |
| Voyage embeddings | voyage-3.5 | ~$0.000 (free tier) |
| **Total per post** | | **~$0.32 USD** |

---

## 10. Error Handling

| Agent / Operation | On failure |
|---|---|
| Agent 0 | Retry once → abort. No research = no post. |
| Agent 1 | Retry once → abort |
| Agent 2 | Retry once → abort. Never pass unvalidated content. |
| Agent 3 | Retry once simplified → abort |
| Agent 4 | Silent fallback to Agent 3. Never abort. |
| URL fetch | Log status, skip, continue. Never abort pipeline. |
| PDF both layers fail | Log, skip document, continue |
| ChromaDB duplicate | Skip silently, return False |

---

## 11. ChromaDB Document Schema

```python
{
    "source_url":   str,
    "title":        str,
    "category":     str,        # article | linkedin_post | research_paper
    "content_hash": str,        # MD5 for dedup
    "ingested_by":  str,        # agent_0 | manual | batch
    "run_id":       str,
    "ingested_at":  str,        # ISO datetime
    "chunk_index":  int         # position within document
}
```

---

## 12. Requirements.txt

```
crewai
chromadb
anthropic
openai
python-dotenv
pyyaml
requests
beautifulsoup4
streamlit
pandas
pydantic-settings
voyageai
pymupdf4llm
pdfplumber
langchain
```
