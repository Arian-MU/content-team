"""Google Drive sync — export approved posts as plain-text .txt files.

How it works:
  1. Reads GDRIVE_ENABLED / GDRIVE_FOLDER_ID / GDRIVE_CREDENTIALS_PATH from settings.
  2. On first call, opens a browser OAuth flow and saves token.json next to credentials.
  3. Subsequent calls are fully silent (token auto-refreshes).
  4. Each post is uploaded as  "{date}_{topic_slug}.txt"  into GDRIVE_FOLDER_ID.
     If a file with that name already exists it is replaced (update, not duplicate).

Dependencies (add to requirements.txt):
    google-auth
    google-auth-oauthlib
    google-auth-httplib2
    google-api-python-client
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from config.settings import settings
from db.queries import get_posts


# OAuth scopes — only Drive file access, not full Drive
_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def is_gdrive_enabled() -> bool:
    """Return True only if Drive sync is switched on AND a folder ID is set."""
    return bool(settings.GDRIVE_ENABLED and settings.GDRIVE_FOLDER_ID.strip())


def _get_service():
    """Build and return an authenticated Drive service object.

    Raises ImportError if google packages are not installed.
    Raises FileNotFoundError if credentials.json is missing.
    Opens a browser on the very first call to complete OAuth consent.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "Google Drive packages not installed. Run: "
            "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        ) from exc

    creds_path = Path(settings.GDRIVE_CREDENTIALS_PATH)
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Google credentials file not found at {creds_path}. "
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    token_path = creds_path.parent / "gdrive_token.json"
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), _SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)


def _slugify(text: str, max_len: int = 50) -> str:
    """Convert a string to a safe filename fragment."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    return slug[:max_len]


def _find_existing_file(service, filename: str, folder_id: str) -> str | None:
    """Return the Drive file ID if a file with this name exists in the folder."""
    query = (
        f"name = '{filename}' and "
        f"'{folder_id}' in parents and "
        f"trashed = false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def export_post_to_drive(post_id: int) -> str:
    """Upload a single post to Google Drive as a .txt file.

    Returns the Drive file URL on success.
    Raises RuntimeError if Drive is not enabled.
    Raises any Google API error as-is.
    """
    if not is_gdrive_enabled():
        raise RuntimeError(
            "Google Drive sync is disabled. Set GDRIVE_ENABLED=true and GDRIVE_FOLDER_ID in .env."
        )

    # Fetch the post
    posts = get_posts()
    post = next((p for p in posts if p.id == post_id), None)
    if post is None:
        raise ValueError(f"Post {post_id} not found.")

    # Build filename: "2026-03-25_ats_tips_international_students.txt"
    date_str = (post.created_at or "")[:10] or "unknown"
    slug = _slugify(post.topic)
    filename = f"{date_str}_{slug}.txt"

    # File body — topic header + content
    body_text = f"Topic: {post.topic}\nDate: {date_str}\nStatus: {post.status}\n\n{post.content_en}"

    try:
        from googleapiclient.http import MediaInMemoryUpload
    except ImportError as exc:
        raise ImportError(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client"
        ) from exc

    service = _get_service()
    folder_id = settings.GDRIVE_FOLDER_ID
    media = MediaInMemoryUpload(body_text.encode("utf-8"), mimetype="text/plain", resumable=False)

    existing_id = _find_existing_file(service, filename, folder_id)

    if existing_id:
        # Update in place — no duplicates
        file = service.files().update(
            fileId=existing_id,
            media_body=media,
        ).execute()
        file_id = file["id"]
    else:
        # Create new
        metadata = {"name": filename, "parents": [folder_id]}
        file = service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
        ).execute()
        file_id = file["id"]

    return f"https://drive.google.com/file/d/{file_id}/view"


def export_all_approved_to_drive() -> dict:
    """Bulk-export all approved/edited/published posts to Drive.

    Returns a summary dict: {exported: int, skipped: int, errors: list[str]}
    """
    if not is_gdrive_enabled():
        raise RuntimeError("Google Drive sync is disabled.")

    posts = [p for p in get_posts() if p.status in ("approved", "edited", "published")]
    exported = 0
    errors: list[str] = []

    for post in posts:
        try:
            export_post_to_drive(post.id)
            exported += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Post {post.id} ({post.topic[:40]}): {exc}")

    return {"exported": exported, "skipped": 0, "errors": errors}
