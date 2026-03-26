"""
trend_fetcher.py
~~~~~~~~~~~~~~~~
Fetches real-time search-demand signals to ground topic generation.

Two free data sources — no API keys required:

1. Google Autocomplete
   Calls the public suggest endpoint and returns the completions that appear
   when someone types a seed keyword into Google.  Geo-targeted to Australia.

2. pytrends (unofficial Google Trends library)
   Returns "related queries" (what people search alongside the seed) split into
   "top" (all-time volume) and "rising" (recently trending / breakout).

Both sources are best-effort: if they fail (network timeout, rate-limit, etc.)
the functions return empty lists so topic generation still works.
"""
from __future__ import annotations

import json
import time
from typing import NamedTuple

import requests

# pytrends is optional — degrade gracefully if not installed
try:
    from pytrends.request import TrendReq  # type: ignore
    _PYTRENDS_AVAILABLE = True
except ImportError:
    _PYTRENDS_AVAILABLE = False

_AUTOCOMPLETE_URL = (
    "https://suggestqueries.google.com/complete/search"
    "?client=firefox&hl=en-AU&gl=au&q={query}"
)
_TIMEOUT = 8  # seconds


class TrendResult(NamedTuple):
    seed: str
    autocomplete: list[str]       # Google autocomplete suggestions
    related_top: list[str]        # Google Trends — top related queries
    related_rising: list[str]     # Google Trends — rising / breakout queries


def _fetch_autocomplete(seed: str) -> list[str]:
    """Return up to 10 Google autocomplete suggestions for *seed*."""
    try:
        url = _AUTOCOMPLETE_URL.format(query=requests.utils.quote(seed))
        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        # Firefox client format: [query, [suggestion1, suggestion2, ...]]
        suggestions = data[1] if len(data) > 1 and isinstance(data[1], list) else []
        # Strip the seed itself if it appears verbatim
        return [s for s in suggestions if s.lower() != seed.lower()][:10]
    except Exception as exc:
        print(f"[trend_fetcher] autocomplete skipped for '{seed}': {exc}")
        return []


def _fetch_related_queries(seeds: list[str], geo: str = "AU") -> dict[str, dict]:
    """Return related queries from Google Trends for a list of seed keywords."""
    if not _PYTRENDS_AVAILABLE:
        print("[trend_fetcher] pytrends not installed — skipping related queries")
        return {}
    try:
        pt = TrendReq(hl="en-AU", tz=600, timeout=(_TIMEOUT, _TIMEOUT))
        # pytrends accepts up to 5 keywords per request
        pt.build_payload(seeds[:5], cat=0, timeframe="today 3-m", geo=geo, gprop="")
        return pt.related_queries()  # {seed: {"top": df, "rising": df}}
    except Exception as exc:
        print(f"[trend_fetcher] pytrends skipped: {exc}")
        return {}


def _df_to_list(df, col: str = "query", limit: int = 10) -> list[str]:
    """Safely convert a pandas DataFrame column to a plain list."""
    try:
        if df is None or df.empty:
            return []
        return df[col].dropna().head(limit).tolist()
    except Exception:
        return []


def fetch_trends(seeds: list[str], geo: str = "AU") -> list[TrendResult]:
    """
    Fetch autocomplete + related-query trends for each seed keyword.

    Parameters
    ----------
    seeds : list[str]
        2-5 short keyword phrases, e.g. ["australia resume", "ATS resume tips"]
    geo   : str
        ISO 3166-1 alpha-2 country code (default "AU")

    Returns
    -------
    list[TrendResult]
        One TrendResult per seed.  Empty lists inside = data source unavailable.
    """
    # Autocomplete: one request per seed with a small delay to avoid throttling
    autocomplete_map: dict[str, list[str]] = {}
    for seed in seeds:
        autocomplete_map[seed] = _fetch_autocomplete(seed)
        time.sleep(0.4)

    # Related queries: batch request (up to 5 seeds at once)
    related_map = _fetch_related_queries(seeds, geo=geo)

    results = []
    for seed in seeds:
        rq = related_map.get(seed, {})
        results.append(TrendResult(
            seed=seed,
            autocomplete=autocomplete_map.get(seed, []),
            related_top=_df_to_list(rq.get("top")),
            related_rising=_df_to_list(rq.get("rising")),
        ))
    return results


def format_for_prompt(results: list[TrendResult], max_per_seed: int = 6) -> str:
    """
    Format TrendResult list into a compact string ready to inject into a prompt.

    Example output:
        == australia resume ==
        Autocomplete: australia resume template, australia resume format 2026, ...
        Rising searches: ats friendly resume australia, resume gaps explanation
        Top searches: resume tips australia, cv vs resume australia

        == ATS resume tips ==
        ...
    """
    if not results:
        return "No trend data available."

    lines: list[str] = []
    for r in results:
        lines.append(f"== {r.seed} ==")
        if r.autocomplete:
            lines.append("Autocomplete: " + ", ".join(r.autocomplete[:max_per_seed]))
        if r.related_rising:
            lines.append("Rising searches: " + ", ".join(r.related_rising[:max_per_seed]))
        if r.related_top:
            lines.append("Top searches: " + ", ".join(r.related_top[:max_per_seed]))
        if not (r.autocomplete or r.related_rising or r.related_top):
            lines.append("(no data returned)")
        lines.append("")

    return "\n".join(lines).strip()
