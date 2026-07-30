"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("slug", name=op.f("uq_organizations_slug")),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_topics_organization_id_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint("organization_id", "slug", name=op.f("uq_topics_organization_id")),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_tags_organization_id_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("organization_id", "slug", name=op.f("uq_tags_organization_id")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_users_organization_id_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("git_path", sa.Text(), nullable=False),
        sa.Column("template_hash", sa.String(), nullable=False),
        sa.Column("model_hint", sa.String(), nullable=True),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_versions")),
        sa.UniqueConstraint("name", "version", name=op.f("uq_prompt_versions_name")),
    )

    op.create_table(
        "generation_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("request", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_input_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_output_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_latency_ms", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=12, scale=6), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_generation_runs_organization_id_organizations")),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], name=op.f("fk_generation_runs_requested_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_runs")),
        sa.UniqueConstraint("organization_id", "idempotency_key", name=op.f("uq_generation_runs_organization_id")),
    )

    op.create_table(
        "reference_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("licence_note", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("ngram_index", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reference_documents")),
    )

    op.create_table(
        "passages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_passages_organization_id_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passages")),
    )

    op.create_table(
        "passage_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("passage_id", sa.UUID(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("paragraphs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("target_band", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.Column("cefr_level", sa.String(), nullable=True),
        sa.Column("readability", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=True),
        sa.Column("genre", sa.String(), nullable=True),
        sa.Column("created_by_run_id", sa.UUID(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_run_id"], ["generation_runs.id"], name=op.f("fk_passage_versions_created_by_run_id_generation_runs")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name=op.f("fk_passage_versions_created_by_user_id_users")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_passage_versions_organization_id_organizations")),
        sa.ForeignKeyConstraint(["passage_id"], ["passages.id"], ondelete="CASCADE", name=op.f("fk_passage_versions_passage_id_passages")),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], name=op.f("fk_passage_versions_topic_id_topics")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passage_versions")),
        sa.UniqueConstraint("organization_id", "content_hash", name=op.f("uq_passage_versions_organization_id")),
        sa.UniqueConstraint("passage_id", "version_no", name=op.f("uq_passage_versions_passage_id")),
    )

    op.create_foreign_key(
        op.f("fk_passages_current_version_id"),
        "passages",
        "passage_versions",
        ["current_version_id"],
        ["id"],
        use_alter=True,
    )

    op.create_table(
        "items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("passage_id", sa.UUID(), nullable=True),
        sa.Column("group_id", sa.UUID(), nullable=True),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_items_organization_id_organizations")),
        sa.ForeignKeyConstraint(["passage_id"], ["passages.id"], name=op.f("fk_items_passage_id_passages")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_items")),
    )

    op.create_table(
        "item_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("answer_key", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("distractor_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("word_limit", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("target_band", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.Column("cefr_level", sa.String(), nullable=True),
        sa.Column("estimated_seconds", sa.Integer(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=True),
        sa.Column("quality_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_run_id", sa.UUID(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_run_id"], ["generation_runs.id"], name=op.f("fk_item_versions_created_by_run_id_generation_runs")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name=op.f("fk_item_versions_created_by_user_id_users")),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE", name=op.f("fk_item_versions_item_id_items")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_versions")),
        sa.UniqueConstraint("item_id", "version_no", name=op.f("uq_item_versions_item_id")),
    )

    op.create_foreign_key(
        op.f("fk_items_current_version_id"),
        "items",
        "item_versions",
        ["current_version_id"],
        ["id"],
        use_alter=True,
    )

    op.create_table(
        "agent_invocations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("agent", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_digest", sa.String(), nullable=True),
        sa.Column("prompt_version_id", sa.UUID(), nullable=True),
        sa.Column("prompt_hash", sa.String(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_per_second", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), server_default="0", nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], name=op.f("fk_agent_invocations_prompt_version_id_prompt_versions")),
        sa.ForeignKeyConstraint(["run_id"], ["generation_runs.id"], ondelete="CASCADE", name=op.f("fk_agent_invocations_run_id_generation_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_invocations")),
    )

    op.create_table(
        "quality_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("rule_code", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("engine_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["generation_runs.id"], name=op.f("fk_quality_checks_run_id_generation_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_checks")),
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], name=op.f("fk_reviews_reviewer_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviews")),
    )

    op.create_table(
        "embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_embeddings")),
        sa.UniqueConstraint("target_type", "target_id", "kind", "model_name", name=op.f("uq_embeddings_target_type")),
    )

    op.create_index("ix_quality_checks_target", "quality_checks", ["target_type", "target_id"])
    op.create_index(
        "ix_quality_checks_failed_rules",
        "quality_checks",
        ["rule_code"],
        postgresql_where=sa.text("passed = false"),
    )
    op.create_index(
        "idx_items_review_queue",
        "items",
        ["organization_id", "status", sa.text("created_at DESC")],
        postgresql_where=sa.text("status IN ('awaiting_review','needs_revision')"),
    )
    op.create_index("idx_items_bank", "items", ["organization_id", "module", "item_type", "status"])
    op.create_index("idx_iv_band", "item_versions", ["target_band", "cefr_level"])
    op.create_index("idx_pv_topic", "passage_versions", ["topic_id", "target_band"])
    op.create_index("idx_ai_run_agent", "agent_invocations", ["run_id", "agent"])
    op.create_index("idx_ai_created", "agent_invocations", [sa.text("created_at DESC")])
    op.execute(
        "CREATE INDEX idx_embeddings_hnsw ON embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("idx_embeddings_hnsw", table_name="embeddings")
    op.drop_index("idx_ai_created", table_name="agent_invocations")
    op.drop_index("idx_ai_run_agent", table_name="agent_invocations")
    op.drop_index("idx_pv_topic", table_name="passage_versions")
    op.drop_index("idx_iv_band", table_name="item_versions")
    op.drop_index("idx_items_bank", table_name="items")
    op.drop_index("idx_items_review_queue", table_name="items")
    op.drop_index("ix_quality_checks_failed_rules", table_name="quality_checks")
    op.drop_index("ix_quality_checks_target", table_name="quality_checks")
    op.drop_table("embeddings")
    op.drop_table("reviews")
    op.drop_table("quality_checks")
    op.drop_table("agent_invocations")
    op.drop_constraint(op.f("fk_items_current_version_id"), "items", type_="foreignkey")
    op.drop_table("item_versions")
    op.drop_table("items")
    op.drop_constraint(op.f("fk_passages_current_version_id"), "passages", type_="foreignkey")
    op.drop_table("passage_versions")
    op.drop_table("passages")
    op.drop_table("reference_documents")
    op.drop_table("generation_runs")
    op.drop_table("prompt_versions")
    op.drop_table("users")
    op.drop_table("tags")
    op.drop_table("topics")
    op.drop_table("organizations")
