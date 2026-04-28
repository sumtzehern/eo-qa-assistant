"""Initial schema: chunks, queries, eval_results, ingestion_jobs.

Revision ID: 0001
Revises:
Create Date: 2026-04-28

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("page_title", sa.Text(), nullable=True),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(), nullable=False, server_default="en"),
        sa.Column("last_crawled", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column("last_modified", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("chunk_id"),
    )
    op.create_index("ix_chunks_source_id", "chunks", ["source_id"])

    op.create_table(
        "queries",
        sa.Column("query_id", sa.String(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("citations", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("no_answer", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("caller_id", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=False, server_default="en"),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("query_id"),
    )
    op.create_index("ix_queries_caller_id", "queries", ["caller_id"])
    op.create_index("ix_queries_session_id", "queries", ["session_id"])

    op.create_table(
        "eval_results",
        sa.Column("eval_id", sa.String(), nullable=False),
        sa.Column("query_id", sa.String(), nullable=False),
        sa.Column("groundedness", sa.Float(), nullable=True),
        sa.Column("retrieval_relevance", sa.Float(), nullable=True),
        sa.Column("citation_accuracy", sa.Float(), nullable=True),
        sa.Column("completeness", sa.Float(), nullable=True),
        sa.Column("hallucination", sa.Boolean(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flag_reason", sa.Text(), nullable=True),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("completed_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.PrimaryKeyConstraint("eval_id"),
    )
    op.create_index("ix_eval_results_query_id", "eval_results", ["query_id"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("chunks_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunks_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunks_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMPTZ(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_ingestion_jobs_source_id", "ingestion_jobs", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_source_id", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_eval_results_query_id", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_queries_session_id", table_name="queries")
    op.drop_index("ix_queries_caller_id", table_name="queries")
    op.drop_table("queries")
    op.drop_index("ix_chunks_source_id", table_name="chunks")
    op.drop_table("chunks")
