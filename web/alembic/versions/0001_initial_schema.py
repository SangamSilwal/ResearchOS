<<<<<<< ours
=======
"""initial schema

Revision ID: 0001
Revises: None
Create Date: 2026-07-19

"""
>>>>>>> theirs
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

<<<<<<< ours
# revision identifiers, used by Alembic.
=======
>>>>>>> theirs
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
<<<<<<< ours
    # required for gen_random_uuid() — Postgres ships this in the
    # pgcrypto extension; server_default here is a belt-and-suspenders
    # fallback since the app also sets UUIDs client-side via uuid.uuid4()
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
=======
    # gen_random_uuid() ships in Postgres' pgcrypto extension -- server-side
    # fallback since the app also sets UUIDs client-side via uuid.uuid4().
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
>>>>>>> theirs

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_unique_constraint(
        "uq_users_provider_provider_id", "users", ["provider", "provider_id"]
    )

    op.create_table(
        "threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False,
                   server_default="New conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_threads_user_id", "threads", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_check_constraint(
        "ck_messages_role", "messages", "role IN ('user', 'assistant')"
    )

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
<<<<<<< ours
        sa.Column("status", sa.String(length=16), nullable=False,
                   server_default="queued"),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("zip_path", sa.Text(), nullable=True),
        sa.Column("task_summary", postgresql.JSONB(), nullable=True),
        sa.Column("flagged_tasks", postgresql.JSONB(), nullable=True),
=======
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("zip_path", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("task_summary", postgresql.JSONB(), nullable=True),
        sa.Column("flagged_tasks", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
>>>>>>> theirs
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_runs_thread_id", "runs", ["thread_id"])
    op.create_unique_constraint("uq_runs_message_id", "runs", ["message_id"])
    op.create_check_constraint(
        "ck_runs_type", "runs", "type IN ('build', 'research')"
    )
    op.create_check_constraint(
<<<<<<< ours
        "ck_runs_status", "runs",
        "status IN ('queued', 'running', 'done', 'error')"
=======
        "ck_runs_status", "runs", "status IN ('queued', 'running', 'done', 'error')"
>>>>>>> theirs
    )

    op.create_table(
        "run_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                   server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True),
                   sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"])
    op.create_index("ix_run_events_created_at", "run_events", ["created_at"])
    op.create_check_constraint(
        "ck_run_events_type", "run_events",
<<<<<<< ours
        "event_type IN ('agent_message', 'node_start', 'node_end')"
=======
        "event_type IN ('agent_message', 'node_start', 'node_end', 'error')"
    )

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
    # BYO providers only -- 'groq' never gets a stored user key, it always
    # uses the platform's own server-side key (see core/config.py).
    op.create_check_constraint(
        "ck_user_api_keys_provider", "user_api_keys",
        "provider IN ('openrouter', 'mistral', 'gemini')"
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
        "agent_role IN ('orchestrator', 'researcher', 'architect_a', 'architect_b', "
        "'judge', 'planner', 'coder', 'critic', 'summarizer')"
    )
    op.create_check_constraint(
        "ck_agent_model_configs_provider", "agent_model_configs",
        "provider IN ('groq', 'openrouter', 'mistral', 'gemini')"
>>>>>>> theirs
    )


def downgrade() -> None:
<<<<<<< ours
=======
    op.drop_table("agent_model_configs")
    op.drop_table("user_api_keys")
>>>>>>> theirs
    op.drop_table("run_events")
    op.drop_table("runs")
    op.drop_table("messages")
    op.drop_table("threads")
<<<<<<< ours
    op.drop_table("users")
=======
    op.drop_table("users")
>>>>>>> theirs
