from __future__ import annotations

import time
from pathlib import Path

import anthropic

from config.settings import settings
from db.queries import get_posts, save_run_log
from pipeline.router import get_model

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "writer.txt"
_STRATEGY_PATH = Path(__file__).parent.parent / "config" / "strategy.yaml"


def _load_strategy() -> str:
    return _STRATEGY_PATH.read_text().strip()


def _load_sample_posts() -> str:
    """Return up to 5 approved posts as style examples, newest first."""
    posts = get_posts(status="approved")[:5]
    if not posts:
        return "No sample posts available yet."
    return "\n\n---\n\n".join(p.content_en for p in posts)


def run(topic: str, validated_insights: str, run_id: str) -> str:
    """Write a LinkedIn post from validated insights.

    Returns the draft post text.
    Raises RuntimeError if both API attempts fail.
    """
    template = _PROMPT_PATH.read_text()
    prompt = (
        template
        .replace("{strategy}", _load_strategy())
        .replace("{sample_posts}", _load_sample_posts())
        .replace("{topic}", topic)
        .replace("{validated_insights}", validated_insights)
    )

    model = get_model("writer")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    last_exc: Exception | None = None
    response = None
    duration_ms = 0
    for attempt in range(2):
        try:
            t0 = time.monotonic()
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            duration_ms = int((time.monotonic() - t0) * 1000)
            break
        except Exception as exc:
            last_exc = exc
            if attempt == 1:
                raise RuntimeError(
                    f"writer_agent failed after 2 attempts: {last_exc}"
                ) from last_exc
            time.sleep(2)

    output = response.content[0].text.strip()  # type: ignore[union-attr]

    save_run_log(
        run_id=run_id,
        agent="writer",
        input=topic,
        output=output,
        model=model,
        tokens_in=response.usage.input_tokens,  # type: ignore[union-attr]
        tokens_out=response.usage.output_tokens,  # type: ignore[union-attr]
        duration_ms=duration_ms,
    )

    return output

