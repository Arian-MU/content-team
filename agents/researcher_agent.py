from __future__ import annotations

import time
from pathlib import Path

from openai import OpenAI

from config.settings import settings
from db.queries import save_research_output, save_run_log
from pipeline.router import get_model
from rag import fetcher, ingestor

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "researcher.txt"
_STATUS_TYPES = ["success", "paywalled", "dead", "blocked", "timeout", "failed"]


def run(topic: str, run_id: str) -> dict:
    """Run deep research on a topic via Perplexity sonar-deep-research.

    Returns:
        {
            "research_report": str,
            "citations": list[str],
            "ingestion_summary": dict[str, list],
        }
    Raises RuntimeError if both API attempts fail.
    """
    template = _PROMPT_PATH.read_text()
    prompt = template.replace("{topic}", topic)

    model = get_model("researcher")
    client = OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai",
    )

    last_exc: Exception | None = None
    response = None
    duration_ms = 0
    for attempt in range(2):
        try:
            t0 = time.monotonic()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            duration_ms = int((time.monotonic() - t0) * 1000)
            break
        except Exception as exc:
            last_exc = exc
            if attempt == 1:
                raise RuntimeError(
                    f"researcher_agent failed after 2 attempts: {last_exc}"
                ) from last_exc
            time.sleep(2)

    raw_report = response.choices[0].message.content  # type: ignore[union-attr]
    citations: list[str] = list(getattr(response, "citations", []) or [])

    # ── Fetch + ingest every citation ──────────────────────────────────────────
    summary: dict[str, list] = {s: [] for s in _STATUS_TYPES}

    for url in citations:
        fetch_result = fetcher.fetch_article(url)
        status = fetch_result["status"]

        if status == "success":
            ingested = ingestor.ingest_url(
                url=url,
                content=fetch_result["content"],
                title=fetch_result["title"],
                category="article",
                ingested_by="researcher_agent",
                run_id=run_id,
            )
            if ingested:
                summary["success"].append(url)
        else:
            summary[status].append({"url": url, "reason": fetch_result["reason"]})

    ingested_count = len(summary["success"])
    failed_count = sum(len(v) for k, v in summary.items() if k != "success")

    save_research_output(
        run_id=run_id,
        topic=topic,
        raw_report=raw_report,
        citations=citations,
        ingested=ingested_count,
        failed=failed_count,
    )

    save_run_log(
        run_id=run_id,
        agent="researcher",
        input=topic,
        output=raw_report[:2000],
        model=model,
        tokens_in=getattr(response.usage, "prompt_tokens", None),  # type: ignore[union-attr]
        tokens_out=getattr(response.usage, "completion_tokens", None),  # type: ignore[union-attr]
        duration_ms=duration_ms,
    )

    return {
        "research_report": raw_report,
        "citations": citations,
        "ingestion_summary": summary,
    }

