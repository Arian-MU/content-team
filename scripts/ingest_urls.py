"""
scripts/ingest_urls.py
----------------------
Batch-ingest URLs from data/urls_to_ingest.txt into ChromaDB.

Usage:
    python scripts/ingest_urls.py [--category CATEGORY] [--urls-file PATH]

File format (one entry per line, lines starting with # are comments):
    https://example.com/article-1
    https://example.com/article-2
    # optional comment

Options:
    --category      ChromaDB category tag (default: "general")
    --urls-file     Path to the URLs file (default: data/urls_to_ingest.txt)
    --dry-run       Print URLs without fetching / ingesting
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when script is run directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rag import fetcher, ingestor

_DEFAULT_URLS_FILE = _PROJECT_ROOT / "data" / "urls_to_ingest.txt"
_RUN_ID = "manual_ingest"


def _load_urls(path: Path) -> list[str]:
    """Read non-empty, non-comment lines from the URLs file."""
    if not path.exists():
        print(f"[ERROR] URLs file not found: {path}", file=sys.stderr)
        sys.exit(1)
    urls = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def _run(urls: list[str], category: str, dry_run: bool) -> None:
    totals: dict[str, int] = {
        "success": 0,
        "duplicate": 0,
        "paywalled": 0,
        "dead": 0,
        "blocked": 0,
        "timeout": 0,
        "failed": 0,
    }

    for i, url in enumerate(urls, 1):
        prefix = f"[{i}/{len(urls)}]"

        if dry_run:
            print(f"{prefix} DRY-RUN  {url}")
            continue

        print(f"{prefix} Fetching {url} …", end=" ", flush=True)
        result = fetcher.fetch_article(url)
        status = result["status"]

        if status != "success":
            totals[status] = totals.get(status, 0) + 1
            print(f"{status.upper()} — {result.get('reason', '')}")
            continue

        ingested = ingestor.ingest_url(
            url=url,
            content=result["content"],
            title=result["title"],
            category=category,
            ingested_by="ingest_urls_script",
            run_id=_RUN_ID,
        )

        if ingested:
            totals["success"] += 1
            print(f"INGESTED -- '{result['title'][:60]}'")
        else:
            totals["duplicate"] += 1
            print("DUPLICATE — skipped")

    if not dry_run:
        print("\n── Summary " + "─" * 40)
        for key, count in totals.items():
            if count:
                print(f"  {key:<12} {count}")
        print("─" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-ingest URLs into ChromaDB")
    parser.add_argument(
        "--category",
        default="general",
        help="ChromaDB category tag (default: general)",
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        default=_DEFAULT_URLS_FILE,
        help=f"Path to URLs file (default: {_DEFAULT_URLS_FILE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print URLs without fetching or ingesting",
    )
    args = parser.parse_args()

    urls = _load_urls(args.urls_file)
    if not urls:
        print("[WARN] No URLs found in file. Nothing to ingest.")
        return

    print(f"Loaded {len(urls)} URL(s) from {args.urls_file}")
    print(f"Category: {args.category}  |  Dry-run: {args.dry_run}\n")

    _run(urls, args.category, args.dry_run)


if __name__ == "__main__":
    main()

