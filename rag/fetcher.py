from __future__ import annotations

import time
import requests
import pdfplumber
import pymupdf4llm
from bs4 import BeautifulSoup
from io import BytesIO

# ── Constants ────────────────────────────────────────────────────────────────────
_TIMEOUT = 15                # seconds for each HTTP request
_POLITE_DELAY = 1.0          # seconds between fetches

_PAYWALL_MARKERS = [
    "subscribe to read",
    "subscription required",
    "sign in to read",
    "create a free account",
    "this article is for subscribers",
    "you've used all your free articles",
    "premium content",
    "members only",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ContentTeamBot/1.0; "
        "+https://github.com/Arian-MU/content-team)"
    )
}


# ── Internal helpers ─────────────────────────────────────────────────────────────

def _is_pdf_url(url: str, content_type: str) -> bool:
    return url.lower().endswith(".pdf") or "application/pdf" in content_type


def _extract_pdf(raw: bytes) -> str:
    """Try pymupdf4llm first, fall back to pdfplumber."""
    try:
        text = pymupdf4llm.to_markdown(BytesIO(raw))
        if text and len(text.strip()) > 50:
            return text.strip()
    except Exception:
        pass

    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if text:
            return text
    except Exception:
        pass

    return ""


def _is_paywalled(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in _PAYWALL_MARKERS)


def _extract_html(html: str) -> tuple[str, str]:
    """Return (title, body_text) from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Remove nav/footer/script/style noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Prefer <article> or <main>, fall back to <body>
    body = soup.find("article") or soup.find("main") or soup.find("body")
    text = body.get_text(separator="\n", strip=True) if body else ""
    return title, text


# ── Public API ───────────────────────────────────────────────────────────────────

def fetch_article(url: str) -> dict:
    """Fetch and extract article content from a URL.

    Returns a dict with keys:
        url, status, title, content, reason (on failure)

    Status values: success | paywalled | dead | blocked | timeout | failed
    Never raises — all exceptions are caught and returned as status.
    """
    result: dict = {"url": url, "title": "", "content": "", "reason": ""}

    try:
        # ── HEAD first (cheap, fast) ────────────────────────────────────────────
        try:
            head = requests.head(
                url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True
            )
        except requests.exceptions.Timeout:
            result["status"] = "timeout"
            result["reason"] = "HEAD request timed out"
            return result
        except requests.exceptions.RequestException as exc:
            result["status"] = "dead"
            result["reason"] = str(exc)
            return result

        if head.status_code == 403:
            result["status"] = "blocked"
            result["reason"] = f"HTTP 403 on HEAD"
            return result
        if head.status_code == 404:
            result["status"] = "dead"
            result["reason"] = "HTTP 404"
            return result
        if head.status_code >= 400:
            result["status"] = "dead"
            result["reason"] = f"HTTP {head.status_code}"
            return result

        content_type = head.headers.get("Content-Type", "")

        # ── GET ─────────────────────────────────────────────────────────────────
        time.sleep(_POLITE_DELAY)
        try:
            resp = requests.get(
                url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True
            )
        except requests.exceptions.Timeout:
            result["status"] = "timeout"
            result["reason"] = "GET request timed out"
            return result
        except requests.exceptions.RequestException as exc:
            result["status"] = "failed"
            result["reason"] = str(exc)
            return result

        if resp.status_code == 403:
            result["status"] = "blocked"
            result["reason"] = "HTTP 403"
            return result
        if resp.status_code >= 400:
            result["status"] = "dead"
            result["reason"] = f"HTTP {resp.status_code}"
            return result

        # ── PDF branch ──────────────────────────────────────────────────────────
        if _is_pdf_url(url, content_type):
            text = _extract_pdf(resp.content)
            if not text:
                result["status"] = "failed"
                result["reason"] = "PDF extraction returned empty text"
                return result
            result["status"] = "success"
            result["title"] = url.split("/")[-1]
            result["content"] = text
            return result

        # ── HTML branch ─────────────────────────────────────────────────────────
        title, text = _extract_html(resp.text)
        if _is_paywalled(text):
            result["status"] = "paywalled"
            result["reason"] = "Paywall markers detected"
            result["title"] = title
            return result

        if not text or len(text.strip()) < 100:
            result["status"] = "failed"
            result["reason"] = "Extracted text too short or empty"
            return result

        result["status"] = "success"
        result["title"] = title
        result["content"] = text.strip()
        return result

    except Exception as exc:
        result["status"] = "failed"
        result["reason"] = f"Unexpected error: {exc}"
        return result

