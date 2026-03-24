from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings
from rag.embedder import embed_single

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def query(
    text: str,
    score_threshold: float = 0.75,
    category: str | None = None,
) -> list[dict]:
    collection = get_collection()
    query_embedding = embed_single(text)
    where = {"category": category} if category else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=20,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    filtered: list[dict] = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = 1 - distance
        if similarity >= score_threshold:
            filtered.append(
                {
                    "content": doc,
                    "source_url": meta.get("source_url"),
                    "category": meta.get("category"),
                    "similarity": round(similarity, 3),
                }
            )

    return filtered


def get_doc_count(category: str | None = None) -> int:
    collection = get_collection()
    if category:
        result = collection.get(where={"category": category}, include=[])
        return len(result["ids"])
    return collection.count()


def document_exists(content_hash: str) -> bool:
    collection = get_collection()
    result = collection.get(
        where={"content_hash": content_hash},
        include=[],
    )
    return len(result["ids"]) > 0

