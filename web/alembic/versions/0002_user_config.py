"""user API keys + per-user agent model configuration

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("encrypted_key", sa.LargeBinary(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_api_keys_user_id", "user_api_keys", ["user_id"])
    op.create_unique_constraint(
        "uq_user_api_keys_user_provider", "user_api_keys", ["user_id", "provider"]
    )
    # BYO providers only — 'anthropic' never gets a stored user key, it
    # always uses the platform's own server-side key.
    op.create_check_constraint(
        "ck_user_api_keys_provider", "user_api_keys",
        "provider IN ('openrouter', 'mistral', 'gemini', 'llama')"
    )

    op.create_table(
        "agent_model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_role", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_model_configs_user_id", "agent_model_configs", ["user_id"])
    op.create_unique_constraint(
        "uq_agent_model_configs_user_role", "agent_model_configs", ["user_id", "agent_role"]
    )
    op.create_check_constraint(
        "ck_agent_model_configs_role", "agent_model_configs",
        "agent_role IN ('orchestrator', 'researcher', 'architect', "
        "'planner', 'coder', 'critic', 'judge')"
    )
    op.create_check_constraint(
        "ck_agent_model_configs_provider", "agent_model_configs",
        "provider IN ('anthropic', 'openrouter', 'mistral', 'gemini', 'llama')"
    )


def downgrade() -> None:
    op.drop_table("agent_model_configs")
    op.drop_table("user_api_keys")