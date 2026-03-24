import voyageai
from config.settings import settings

_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    """Lazy-initialise the Voyage AI client (only connects on first call)."""
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of texts. Returns one embedding vector per text."""
    if not texts:
        return []
    client = _get_client()
    result = client.embed(texts, model="voyage-3.5", input_type="document")
    return result.embeddings


def embed_single(text: str) -> list[float]:
    """Embed a single text string. Convenience wrapper around embed()."""
    return embed([text])[0]

