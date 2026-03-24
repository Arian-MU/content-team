from __future__ import annotations

import time
from pathlib import Path

import anthropic

from config.settings import settings
from db.queries import save_run_log
from pipeline.router import get_model

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "optimiser.txt"


def run(draft_post: str, run_id: str) -> str:
    """Optimise a LinkedIn post draft for hook strength and readability.

    Returns the improved post, or `draft_post` unchanged if the API call fails
    (silent fallback — optimiser never aborts the pipeline).
    """
    template = _PROMPT_PATH.read_text()
    prompt = template.replace("{draft_post}", draft_post)

    model = get_model("optimiser")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        t0 = time.monotonic()
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        output = response.content[0].text.strip()

        save_run_log(
            run_id=run_id,
            agent="optimiser",
            input=draft_post[:500],
            output=output,
            model=model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            duration_ms=duration_ms,
        )

        return output

    except Exception:
        # Silent fallback — return writer output unchanged, never abort
        return draft_post

