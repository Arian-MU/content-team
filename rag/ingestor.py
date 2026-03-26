from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag import chromadb_client, embedder

# ── Chunker config — KISS, battle-tested ─────────────────────────────────────
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=102,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(text: str) -> list[str]:
    """Split text into chunks with 20% overlap."""
    return _splitter.split_text(text)


def ingest_url(
    url: str,
    content: str,
    title: str,
    category: str,
    ingested_by: str,
    run_id: str,
) -> bool:
    """Chunk, embed, and store content in ChromaDB.

    Returns True if newly ingested, False if duplicate or empty.
    Never raises — errors logged and False returned.
    """
    content_hash = hashlib.md5(content.encode()).hexdigest()

    # ── Dedup check ──────────────────────────────────────────────────────────
    if chromadb_client.document_exists(content_hash):
        return False

    # ── Chunk ────────────────────────────────────────────────────────────────
    chunks = chunk_text(content)
    if not chunks:
        return False

    # ── Embed all chunks in one batch call ───────────────────────────────────
    try:
        embeddings = embedder.embed(chunks)
    except Exception as exc:  # e.g. VoyageAI RateLimitError on free tier
        print(f"[ingestor] Embedding skipped ({type(exc).__name__}): {exc}")
        return False

    # ── Build metadata ───────────────────────────────────────────────────────
    ingested_at = datetime.now(timezone.utc).isoformat()
    metadatas = [
        {
            "source_url": url,
            "title": title,
            "category": category,
            "content_hash": content_hash,
            "ingested_by": ingested_by,
            "run_id": run_id,
            "ingested_at": ingested_at,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    # ── Store ────────────────────────────────────────────────────────────────
    collection = chromadb_client.get_collection()
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=[f"{content_hash}_{i}" for i in range(len(chunks))],
    )

    return True

