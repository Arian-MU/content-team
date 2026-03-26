#!/usr/bin/env python
"""
End-to-end test of the trend fetcher pipeline.
Run with: .venv/bin/python scripts/test_trend_fetcher.py
"""
import sys, time, requests
sys.path.insert(0, ".")

print()
print("=" * 60)
print("STEP 1  —  Google Autocomplete (raw HTTP)")
print("=" * 60)

seeds = [
    "australia resume",
    "ATS resume tips",
    "job search australia international student",
    "linkedin networking australia",
]

autocomplete_results = {}
for seed in seeds:
    url = (
        "https://suggestqueries.google.com/complete/search"
        f"?client=firefox&hl=en-AU&gl=au&q={requests.utils.quote(seed)}"
    )
    print(f'\nSeed : "{seed}"')
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        suggestions = data[1] if len(data) > 1 and isinstance(data[1], list) else []
        suggestions = [s for s in suggestions if s.lower() != seed.lower()][:10]
        autocomplete_results[seed] = suggestions
        print(f"  HTTP status : {resp.status_code}")
        print(f"  Suggestions : {len(suggestions)} returned")
        for s in suggestions:
            print(f"    - {s}")
    except Exception as exc:
        autocomplete_results[seed] = []
        print(f"  ERROR: {type(exc).__name__}: {exc}")
    time.sleep(0.4)

print()
print("=" * 60)
print("STEP 2  —  pytrends Related Queries (Google Trends, AU, 90d)")
print("=" * 60)

related_top = {}
related_rising = {}

try:
    from pytrends.request import TrendReq
    print(f"\nImporting pytrends ... OK")
    pt = TrendReq(hl="en-AU", tz=600, timeout=(8, 8))
    print("Building payload for all seeds ...")
    pt.build_payload(seeds[:5], cat=0, timeframe="today 3-m", geo="AU", gprop="")
    print("Fetching related_queries() ...")
    related = pt.related_queries()
    print(f"Response received for {len(related)} seed(s).\n")

    for seed in seeds:
        rq = related.get(seed, {})
        top_df    = rq.get("top")
        rising_df = rq.get("rising")

        top    = top_df["query"].head(6).tolist()    if top_df    is not None and not top_df.empty    else []
        rising = rising_df["query"].head(6).tolist() if rising_df is not None and not rising_df.empty else []

        related_top[seed]    = top
        related_rising[seed] = rising

        print(f'Seed    : "{seed}"')
        print(f"  Top ({len(top)})    : {top}")
        print(f"  Rising ({len(rising)}) : {rising}")
        print()

except ImportError:
    print("  pytrends not installed — skipping")
except Exception as exc:
    print(f"  ERROR: {type(exc).__name__}: {exc}")

print()
print("=" * 60)
print("STEP 3  —  format_for_prompt() output  (what the AI sees)")
print("=" * 60)
print()

from rag.trend_fetcher import fetch_trends, format_for_prompt, TrendResult

# Build TrendResult objects from data we already fetched
manual_results = [
    TrendResult(
        seed=seed,
        autocomplete=autocomplete_results.get(seed, []),
        related_top=related_top.get(seed, []),
        related_rising=related_rising.get(seed, []),
    )
    for seed in seeds
]
prompt_block = format_for_prompt(manual_results)
print(prompt_block)

print()
print("=" * 60)
print("STEP 4  —  Full fetch_trends() call (as used in production)")
print("=" * 60)
print()

live_results = fetch_trends(seeds, geo="AU")
live_block   = format_for_prompt(live_results)
print(live_block)

print()
print("=" * 60)
print("ALL STEPS COMPLETE")
print("=" * 60)
