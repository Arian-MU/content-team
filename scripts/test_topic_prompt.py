#!/usr/bin/env python
"""
Show exactly what is sent to, and received from, the LLM during topic generation.
Run with: .venv/bin/python scripts/test_topic_prompt.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, ".")

from config.settings import settings
from db.queries import get_posts
from rag.trend_fetcher import fetch_trends, format_for_prompt

PROMPT_PATH = Path("prompts/topic_agent.txt")
STRATEGY_PATH = Path("config/strategy.yaml")

DIVIDER = "=" * 70

# ── 1. Load each component separately so we can inspect them ─────────────────

print()
print(DIVIDER)
print("COMPONENT 1 — Strategy (from config/strategy.yaml)")
print(DIVIDER)
strategy = STRATEGY_PATH.read_text().strip()
print(strategy)

print()
print(DIVIDER)
print("COMPONENT 2 — Post History (from SQLite — approved posts only)")
print(DIVIDER)
posts = get_posts(status="approved")
if posts:
    post_history = "\n".join(f"- {p.topic}" for p in posts[:30])
else:
    post_history = "No previous posts yet."
print(post_history)

print()
print(DIVIDER)
print("COMPONENT 3 — Trend Data  (Google Autocomplete + pytrends, live fetch)")
print(DIVIDER)
seeds = [
    "australia resume",
    "ATS resume tips",
    "job search australia international student",
    "linkedin australia jobs",
]
print(f"Fetching trends for seeds: {seeds}")
print()
results = fetch_trends(seeds, geo="AU")
trending_searches = format_for_prompt(results)
print(trending_searches)

# ── 2. Assemble the final prompt exactly as topic_agent.py does ──────────────

template = PROMPT_PATH.read_text()
full_prompt = (
    template
    .replace("{strategy}", strategy)
    .replace("{post_history}", post_history)
    .replace("{trending_searches}", trending_searches)
    .replace("{current_date}", date.today().isoformat())
)

print()
print(DIVIDER)
print("FULL PROMPT SENT TO LLM  (every word Claude sees)")
print(DIVIDER)
print(full_prompt)
print()
print(f"[Prompt length: {len(full_prompt):,} characters / ~{len(full_prompt)//4} tokens]")

# ── 3. Call Claude and capture the raw output ────────────────────────────────

print()
print(DIVIDER)
print("CALLING LLM — claude-haiku-4-5  (TEST_MODE=true)")
print(DIVIDER)
print("Waiting for response...")

import anthropic, time
from pipeline.router import get_model

model = get_model("topic_agent")
print(f"Model resolved: {model}")

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
t0 = time.monotonic()
response = client.messages.create(
    model=model,
    max_tokens=1200,
    messages=[{"role": "user", "content": full_prompt}],
)
elapsed = time.monotonic() - t0

print(f"Response received in {elapsed:.1f}s")
print(f"Tokens in : {response.usage.input_tokens}")
print(f"Tokens out: {response.usage.output_tokens}")

raw_output = response.content[0].text.strip()

print()
print(DIVIDER)
print("RAW LLM OUTPUT  (exactly what Claude returned)")
print(DIVIDER)
print(raw_output)

# ── 4. Parse into final topic list ───────────────────────────────────────────

print()
print(DIVIDER)
print("PARSED TOPICS  (what appears in the Generate tab)")
print(DIVIDER)
topics = [ln.strip() for ln in raw_output.splitlines() if ln.strip() and ln.strip()[0].isdigit()]
for t in topics:
    print(t)

print()
print(DIVIDER)
print(f"DONE — {len(topics)} topics generated")
print(DIVIDER)
