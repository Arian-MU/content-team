from dataclasses import dataclass
from typing import Optional


@dataclass
class Post:
    id: int
    topic: str
    content_en: str
    model_writer: Optional[str]
    model_optimiser: Optional[str]
    status: str
    run_id: Optional[str]
    created_at: str
    published_at: Optional[str]


@dataclass
class ResearchOutput:
    id: int
    run_id: str
    topic: str
    raw_report: str
    citations: str          # JSON-encoded list of URLs
    ingested_count: Optional[int]
    skipped_count: Optional[int]
    failed_count: Optional[int]
    cost_usd: Optional[float]
    created_at: str


@dataclass
class Topic:
    id: int
    topic: str
    source: str
    source_url: Optional[str]
    used: int
    created_at: str


@dataclass
class RunLog:
    id: int
    run_id: str
    agent: str
    input: Optional[str]
    output: Optional[str]
    model: Optional[str]
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    cost_usd: Optional[float]
    duration_ms: Optional[int]
    created_at: str

