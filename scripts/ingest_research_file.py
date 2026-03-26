#!/usr/bin/env python
"""
Ingest a local research report .md/.txt file directly into the Knowledge Base.

Usage:
    python scripts/ingest_research_file.py <path_to_file>
"""
import sys
import re
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.ingestor import ingest_url
from db.queries import save_research_output


def parse_research_md(text: str):
    """Same logic as _parse_research_md in pages/3_Knowledge_Base.py."""
    # Title
    title = ""
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        stripped = re.sub(r'【\d+†[^\】]*】', '', stripped).strip()
        stripped = re.sub(r'citeturn\w+', '', stripped).strip()
        if stripped:
            title = stripped
            break

    # Bare URLs
    urls = []
    seen: set = set()
    for url in re.findall(r'https?://[^\s\)\]"\'>,]+', text):
        url = url.rstrip(".,;)")
        if url not in seen:
            seen.add(url)
            urls.append(url)

    # References section
    ref_re = re.compile(
        r'^#{1,3}\s*(references?|sources?|bibliography|citations?)\s*$',
        re.IGNORECASE | re.MULTILINE,
    )
    citations = []
    m = ref_re.search(text)
    if m:
        ref_text = text[m.end():]
        nh = re.search(r'^#{1,3}\s', ref_text, re.MULTILINE)
        if nh:
            ref_text = ref_text[:nh.start()]
        for line in ref_text.splitlines():
            clean = re.sub(r'^[\s\-\*•\d\.]+', '', line).strip()
            clean = re.sub(r'【\d+†[^\】]*】', '', clean).strip()
            clean = re.sub(r'citeturn\w+', '', clean).strip()
            if clean:
                citations.append(clean)

    if not citations:
        citations = urls

    return title, urls, citations


def main():
    file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not file_path or not file_path.exists():
        print("Usage: python scripts/ingest_research_file.py <path_to_file>")
        sys.exit(1)

    text = file_path.read_text(encoding="utf-8")
    title, urls, citations = parse_research_md(text)

    print(f"\n{'='*60}")
    print(f"File      : {file_path.name}")
    print(f"Title     : {title[:80]}")
    print(f"URLs      : {len(urls)}")
    print(f"Citations : {len(citations)}")
    if citations:
        for c in citations[:5]:
            print(f"  • {c[:100]}")
        if len(citations) > 5:
            print(f"  … +{len(citations)-5} more")
    print(f"{'='*60}\n")

    run_id = str(uuid.uuid4())

    print("Ingesting into ChromaDB…")
    ok = ingest_url(
        url=f"manual_research:{run_id}",
        content=text,
        title=title or file_path.stem,
        category="research_paper",
        ingested_by="manual_research",
        run_id=run_id,
    )

    print("Saving to SQLite…")
    save_research_output(
        run_id=run_id,
        topic=title or file_path.stem,
        raw_report=text,
        citations=citations,
        ingested=1 if ok else 0,
        skipped=0 if ok else 1,
        failed=0,
        cost_usd=0.0,
    )

    if ok:
        print(f"\n✅ Ingested successfully (run_id={run_id})")
        print(f"   {len(citations)} citation(s) saved to SQLite.")
        print(f"   You can browse it in the Knowledge Base → Browse Sources.")
    else:
        print(f"\n⏭️  Skipped — report may already be in the KB, or embedding failed.")
        print(f"   SQLite record still saved (run_id={run_id})")


if __name__ == "__main__":
    main()
