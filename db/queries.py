import json
from typing import Optional

from db.database import get_connection
from db.models import Post, ResearchOutput, RunLog, Topic


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

def save_post(
    topic: str,
    content_en: str,
    model_writer: Optional[str],
    model_optimiser: Optional[str],
    run_id: Optional[str],
    status: str = "approved",
) -> int:
    """Insert a new post row and return its id."""
    sql = """
        INSERT INTO posts (topic, content_en, model_writer, model_optimiser, run_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(sql, (topic, content_en, model_writer, model_optimiser, run_id, status))
        conn.commit()
        return cursor.lastrowid


def update_post_status(post_id: int, status: str) -> None:
    """Update the status field of an existing post."""
    with get_connection() as conn:
        conn.execute("UPDATE posts SET status = ? WHERE id = ?", (status, post_id))
        conn.commit()


def get_posts(status: Optional[str] = None) -> list[Post]:
    """Return all posts, optionally filtered by status."""
    with get_connection() as conn:
        if status is None:
            rows = conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
    return [Post(**dict(row)) for row in rows]


def delete_post(post_id: int) -> None:
    """Hard-delete a post by id."""
    with get_connection() as conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Research outputs
# ---------------------------------------------------------------------------

def save_research_output(
    run_id: str,
    topic: str,
    raw_report: str,
    citations: list[str],
    ingested: int = 0,
    skipped: int = 0,
    failed: int = 0,
    cost_usd: Optional[float] = None,
) -> int:
    """Persist a researcher agent output. citations is serialised to JSON."""
    sql = """
        INSERT INTO research_outputs
            (run_id, topic, raw_report, citations, ingested_count, skipped_count, failed_count, cost_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(
            sql,
            (run_id, topic, raw_report, json.dumps(citations), ingested, skipped, failed, cost_usd),
        )
        conn.commit()
        return cursor.lastrowid


def get_research_output(run_id: str) -> Optional[ResearchOutput]:
    """Return the research output for a run_id, or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM research_outputs WHERE run_id = ?", (run_id,)
        ).fetchone()
    if row is None:
        return None
    return ResearchOutput(**dict(row))


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

def add_topic(topic: str, source: str, source_url: Optional[str] = None) -> int:
    """Insert a new topic and return its id."""
    sql = "INSERT INTO topics (topic, source, source_url) VALUES (?, ?, ?)"
    with get_connection() as conn:
        cursor = conn.execute(sql, (topic, source, source_url))
        conn.commit()
        return cursor.lastrowid


def get_unused_topics(limit: int = 5) -> list[Topic]:
    """Return up to `limit` topics that have not been used yet."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM topics WHERE used = 0 ORDER BY created_at ASC LIMIT ?", (limit,)
        ).fetchall()
    return [Topic(**dict(row)) for row in rows]


def mark_topic_used(topic_id: int) -> None:
    """Mark a topic as used."""
    with get_connection() as conn:
        conn.execute("UPDATE topics SET used = 1 WHERE id = ?", (topic_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Run logs
# ---------------------------------------------------------------------------

def save_run_log(
    run_id: str,
    agent: str,
    input: Optional[str] = None,
    output: Optional[str] = None,
    model: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    cost_usd: Optional[float] = None,
    duration_ms: Optional[int] = None,
) -> int:
    """Persist a single agent run log entry and return its id."""
    sql = """
        INSERT INTO run_logs
            (run_id, agent, input, output, model, tokens_in, tokens_out, cost_usd, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(
            sql,
            (run_id, agent, input, output, model, tokens_in, tokens_out, cost_usd, duration_ms),
        )
        conn.commit()
        return cursor.lastrowid

