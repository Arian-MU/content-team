from __future__ import annotations

import time
from pathlib import Path

from openai import OpenAI

from config.settings import settings
from db.queries import save_run_log
from pipeline.router import get_model

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "fact_checker.txt"


def run(topic: str, insights: str, citations: list[str], run_id: str) -> str:
    """Validate every claim in `insights` against the provided citations.

    Returns the full fact-checked output as a string (claims marked ✅ / [FLAG],
    plus ### Removed Claims and ### Validation Notes sections).
    Raises RuntimeError if both API attempts fail.
    """
    citations_text = "\n".join(f"{i + 1}. {url}" for i, url in enumerate(citations))

    template = _PROMPT_PATH.read_text()
    prompt = (
        template
        .replace("{topic}", topic)
        .replace("{insights}", insights)
        .replace("{citations}", citations_text)
    )

    model = get_model("fact_checker")
    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
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
                    f"fact_checker_agent failed after 2 attempts: {last_exc}"
                ) from last_exc
            time.sleep(2)

    output = response.choices[0].message.content.strip()  # type: ignore[union-attr]

    save_run_log(
        run_id=run_id,
        agent="fact_checker",
        input=topic,
        output=output,
        model=model,
        tokens_in=getattr(response.usage, "prompt_tokens", None),  # type: ignore[union-attr]
        tokens_out=getattr(response.usage, "completion_tokens", None),  # type: ignore[union-attr]
        duration_ms=duration_ms,
    )

    return output

