import sqlite3
from pathlib import Path

from config.settings import settings

_CREATE_POSTS = """
CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    content_en      TEXT NOT NULL,
    model_writer    TEXT,
    model_optimiser TEXT,
    status          TEXT DEFAULT 'approved',
    run_id          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at    TIMESTAMP
);
"""

_CREATE_RESEARCH_OUTPUTS = """
CREATE TABLE IF NOT EXISTS research_outputs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL,
    topic          TEXT NOT NULL,
    raw_report     TEXT NOT NULL,
    citations      TEXT NOT NULL,
    ingested_count INTEGER,
    skipped_count  INTEGER,
    failed_count   INTEGER,
    cost_usd       REAL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_TOPICS = """
CREATE TABLE IF NOT EXISTS topics (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    topic      TEXT NOT NULL,
    source     TEXT DEFAULT 'manual',
    source_url TEXT,
    used       INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_RUN_LOGS = """
CREATE TABLE IF NOT EXISTS run_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    agent       TEXT NOT NULL,
    input       TEXT,
    output      TEXT,
    model       TEXT,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    cost_usd    REAL,
    duration_ms INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to Row."""
    db_path = Path(settings.SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Create all tables if they don't already exist."""
    with get_connection() as conn:
        conn.execute(_CREATE_POSTS)
        conn.execute(_CREATE_RESEARCH_OUTPUTS)
        conn.execute(_CREATE_TOPICS)
        conn.execute(_CREATE_RUN_LOGS)
        conn.commit()

