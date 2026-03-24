from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import anthropic

from config.settings import settings
from db.queries import get_posts, save_run_log
from pipeline.router import get_model

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "topic_agent.txt"
_STRATEGY_PATH = Path(__file__).parent.parent / "config" / "strategy.yaml"


def _load_strategy() -> str:
    return _STRATEGY_PATH.read_text().strip()


def _load_post_history() -> str:
    posts = get_posts(status="approved")
    if not posts:
        return "No previous posts yet."
    return "\n".join(f"- {p.topic}" for p in posts[:30])


def run(run_id: str) -> list[str]:
    """Generate 10 topic ideas.

    Returns a list of raw topic lines from the numbered list, e.g.:
        ["1. How ATS systems rank ... | Why now | https://...", ...]
    Raises RuntimeError if both API attempts fail.
    """
    template = _PROMPT_PATH.read_text()
    prompt = (
        template
        .replace("{strategy}", _load_strategy())
        .replace("{post_history}", _load_post_history())
        .replace("{current_date}", date.today().isoformat())
    )

    model = get_model("topic_agent")
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
                    f"topic_agent failed after 2 attempts: {last_exc}"
                ) from last_exc
            time.sleep(2)

    output = response.content[0].text.strip()  # type: ignore[union-attr]

    save_run_log(
        run_id=run_id,
        agent="topic_agent",
        input=f"date={date.today().isoformat()}",
        output=output,
        model=model,
        tokens_in=response.usage.input_tokens,  # type: ignore[union-attr]
        tokens_out=response.usage.output_tokens,  # type: ignore[union-attr]
        duration_ms=duration_ms,
    )

    # Parse numbered list — keep lines that start with a digit
    lines = [ln.strip() for ln in output.splitlines() if ln.strip() and ln[0].isdigit()]
    return lines

