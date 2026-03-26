from __future__ import annotations

import uuid

from agents import (
    analyst_agent,
    fact_checker_agent,
    optimiser_agent,
    researcher_agent,
    topic_agent,
    writer_agent,
)
from db.queries import save_post
from pipeline.router import get_model


def suggest_topics(run_id: str | None = None) -> list[str]:
    """Generate 10 topic ideas via topic_agent.

    Returns a list of raw numbered lines, e.g.:
        ["1. How ATS systems ... | Why now | https://...", ...]
    """
    if run_id is None:
        run_id = str(uuid.uuid4())
    return topic_agent.run(run_id=run_id)


def run(topic: str, run_id: str | None = None) -> dict:
    """Run the full content-generation pipeline for a given topic.

    Sequence:
        researcher → analyst → fact_checker → writer → optimiser → save_post

    Returns:
        {
            "run_id":            str,
            "topic":             str,
            "post_id":           int,
            "final_post":        str,
            "ingestion_summary": dict,
        }

    Raises RuntimeError (from any agent) if a non-recoverable failure occurs.
    The optimiser silently falls back to the writer output — it never raises.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    # ── Step 1: Research ────────────────────────────────────────────────────────
    research_result = researcher_agent.run(topic=topic, run_id=run_id)
    research_report    = research_result["research_report"]
    citations          = research_result["citations"]
    ingestion_summary  = research_result["ingestion_summary"]

    # ── Step 2: Analyse ─────────────────────────────────────────────────────────
    analyst_output = analyst_agent.run(
        topic=topic,
        research_report=research_report,
        run_id=run_id,
    )

    # ── Step 3: Fact-check ──────────────────────────────────────────────────────
    validated_insights = fact_checker_agent.run(
        topic=topic,
        insights=analyst_output,
        citations=citations,
        run_id=run_id,
    )

    # ── Step 4: Write ────────────────────────────────────────────────────────────
    draft_post = writer_agent.run(
        topic=topic,
        validated_insights=validated_insights,
        run_id=run_id,
    )

    # ── Step 5: Optimise (silent fallback on failure) ────────────────────────────
    final_post = optimiser_agent.run(draft_post=draft_post, run_id=run_id)

    # ── Step 6: Persist ─────────────────────────────────────────────────────────
    post_id = save_post(
        topic=topic,
        content_en=final_post,
        model_writer=get_model("writer"),
        model_optimiser=get_model("optimiser"),
        run_id=run_id,
    )

    return {
        "run_id":            run_id,
        "topic":             topic,
        "post_id":           post_id,
        "final_post":        final_post,
        "ingestion_summary": ingestion_summary,
    }


def run_from_research(
    topic: str,
    research_report: str,
    citations: list[str],
    run_id: str | None = None,
) -> dict:
    """Run steps 2-5 of the pipeline using a pre-supplied research report.

    Skips the researcher agent entirely — useful when you have an external
    research document (e.g. from ChatGPT Deep Research) and want to feed it
    directly into analyst → fact_checker → writer → optimiser.

    Returns:
        {
            "run_id":     str,
            "topic":      str,
            "post_id":    int,
            "final_post": str,
        }
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    # ── Step 2: Analyse ─────────────────────────────────────────────────────────
    analyst_output = analyst_agent.run(
        topic=topic,
        research_report=research_report,
        run_id=run_id,
    )

    # ── Step 3: Fact-check ──────────────────────────────────────────────────────
    validated_insights = fact_checker_agent.run(
        topic=topic,
        insights=analyst_output,
        citations=citations,
        run_id=run_id,
    )

    # ── Step 4: Write ───────────────────────────────────────────────────────────
    draft_post = writer_agent.run(
        topic=topic,
        validated_insights=validated_insights,
        run_id=run_id,
    )

    # ── Step 5: Optimise (silent fallback) ─────────────────────────────────────
    final_post = optimiser_agent.run(draft_post=draft_post, run_id=run_id)

    # ── Step 6: Persist ─────────────────────────────────────────────────────────
    post_id = save_post(
        topic=topic,
        content_en=final_post,
        model_writer=get_model("writer"),
        model_optimiser=get_model("optimiser"),
        run_id=run_id,
        status="draft",
    )

    return {
        "run_id":     run_id,
        "topic":      topic,
        "post_id":    post_id,
        "final_post": final_post,
    }

