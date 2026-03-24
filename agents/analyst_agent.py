from __future__ import annotations

import time
from pathlib import Path

import anthropic

from config.settings import settings
from db.queries import save_run_log
from pipeline.router import get_model
from rag import chromadb_client

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analyst.txt"


def _format_rag_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant knowledge base snippets found."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] {chunk['content']}\nSource: {chunk.get('source_url', 'unknown')}\n")
    return "\n".join(parts)


def run(topic: str, research_report: str, run_id: str) -> str:
    """Synthesise raw research + RAG chunks into prioritised insights.

    Returns the full analyst output as a string (structured with ### headers).
    Raises RuntimeError if both API attempts fail.
    """
    rag_chunks = chromadb_client.query(topic)

    template = _PROMPT_PATH.read_text()
    prompt = (
        template
        .replace("{topic}", topic)
        .replace("{research_report}", research_report)
        .replace("{rag_chunks}", _format_rag_chunks(rag_chunks))
    )

    model = get_model("analyst")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    last_exc: Exception | None = None
    response = None
    duration_ms = 0
    for attempt in range(2):
        try:
            t0 = time.monotonic()
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            duration_ms = int((time.monotonic() - t0) * 1000)
            break
        except Exception as exc:
            last_exc = exc
            if attempt == 1:
                raise RuntimeError(
                    f"analyst_agent failed after 2 attempts: {last_exc}"
                ) from last_exc
            time.sleep(2)

    output = response.content[0].text.strip()  # type: ignore[union-attr]

    save_run_log(
        run_id=run_id,
        agent="analyst",
        input=topic,
        output=output,
        model=model,
        tokens_in=response.usage.input_tokens,  # type: ignore[union-attr]
        tokens_out=response.usage.output_tokens,  # type: ignore[union-attr]
        duration_ms=duration_ms,
    )

    return output

