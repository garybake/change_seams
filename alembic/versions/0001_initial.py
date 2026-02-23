"""initial

Revision ID: 0001
Revises:
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("purpose", sa.String(length=256), nullable=True),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column("expected_inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expected_outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version", name="uq_prompt_key_version"),
    )
    op.create_index(op.f("ix_prompt_templates_key"), "prompt_templates", ["key"], unique=False)

    op.create_table(
        "observation_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("agent_response", sa.Text(), nullable=False),
        sa.Column("prompt_key", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("policy_mode", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_observation_logs_trace_id"), "observation_logs", ["trace_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_observation_logs_trace_id"), table_name="observation_logs")
    op.drop_table("observation_logs")
    op.drop_index(op.f("ix_prompt_templates_key"), table_name="prompt_templates")
    op.drop_table("prompt_templates")
