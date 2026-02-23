"""seed default prompt

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools.

Use the available tools to help answer the user's question accurately.
If you use a tool, explain what you found. If you cannot answer something,
say so clearly rather than guessing.

Be concise and direct in your responses."""


def upgrade() -> None:
    prompt_templates = sa.table(
        "prompt_templates",
        sa.column("key", sa.String),
        sa.column("version", sa.Integer),
        sa.column("content", sa.Text),
        sa.column("purpose", sa.String),
        sa.column("owner", sa.String),
        sa.column("expected_inputs", sa.JSON),
        sa.column("expected_outputs", sa.JSON),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        prompt_templates,
        [
            {
                "key": "agent.system",
                "version": 1,
                "content": DEFAULT_SYSTEM_PROMPT,
                "purpose": "Main system prompt for the agent",
                "owner": "platform-team",
                "expected_inputs": {"user_message": "string"},
                "expected_outputs": {"answer": "string"},
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM prompt_templates WHERE key = 'agent.system' AND version = 1")
