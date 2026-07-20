"""
Database schema.

Adapted from the design on the `web/backend/database_models` branch,
reconciled with what's actually wired up elsewhere in this codebase:

- AgentRole now has one entry per field in core.config.Settings that
  actually drives an agent (including architect_a/architect_b/judge and
  summarizer, which the original draft was missing/misnamed).
- LLMProvider is limited to the four providers llm/router.py actually
  implements (groq, gemini, mistral, openrouter). The draft's
  'anthropic' and 'llama' aren't wired to anything in this repo, so
  they're left out rather than shipping selectable options that would
  fail at run time.
- 'groq' is the platform-default provider (the app's own server-side
  key, from core.config.settings.groq_api_key) and is deliberately NOT
  a valid value in UserApiKey.provider -- there's nothing for a user to
  bring for it. gemini/mistral/openrouter are BYO-only: a run falls
  back to the platform default for a role if the user picked one of
  these providers but hasn't saved a key for it (see
  web/config_resolution.py).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from web.database import Base


class OAuthProvider(str, enum.Enum):
    google = "google"
    github = "github"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class RunType(str, enum.Enum):
    build = "build"
    research = "research"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"


class RunEventType(str, enum.Enum):
    agent_message = "agent_message"
    node_start = "node_start"
    node_end = "node_end"
    error = "error"


class LLMProvider(str, enum.Enum):
    """BYO providers a user can store a key for. See module docstring."""
    openrouter = "openrouter"
    mistral = "mistral"
    gemini = "gemini"


class AgentRole(str, enum.Enum):
    """Pipeline roles a user can assign a specific provider/model to."""
    orchestrator = "orchestrator"
    researcher = "researcher"
    architect_a = "architect_a"
    architect_b = "architect_b"
    judge = "judge"
    planner = "planner"
    coder = "coder"
    critic = "critic"
    summarizer = "summarizer"


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)       # OAuthProvider
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)   # OAuth subject/sub
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    threads: Mapped[list["Thread"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["UserApiKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    agent_model_configs: Mapped[list["AgentModelConfig"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_users_provider_provider_id"),
    )


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New conversation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="threads")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    runs: Mapped[list["Run"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # MessageRole
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    thread: Mapped["Thread"] = relationship(back_populates="messages")
    run: Mapped[Optional["Run"]] = relationship(
        back_populates="message", uselist=False, foreign_keys="Run.message_id"
    )


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)          # RunType
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=RunStatus.queued.value)
    zip_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    flagged_tasks: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    thread: Mapped["Thread"] = relationship(back_populates="runs")
    message: Mapped[Optional["Message"]] = relationship(
        back_populates="run", foreign_keys=[message_id]
    )
    events: Mapped[list["RunEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunEvent.created_at"
    )


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # RunEventType
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    run: Mapped["Run"] = relationship(back_populates="events")


class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_api_keys_user_provider"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)

    # AES-256-GCM ciphertext + its nonce (see web/crypto.py). The raw key
    # is never stored, logged, or returned by any API response.
    encrypted_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="api_keys")


class AgentModelConfig(Base):
    __tablename__ = "agent_model_configs"
    __table_args__ = (
        UniqueConstraint("user_id", "agent_role", name="uq_agent_model_configs_user_role"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_role: Mapped[str] = mapped_column(String(32), nullable=False)   # AgentRole
    provider: Mapped[str] = mapped_column(String(32), nullable=False)     # "groq" or an LLMProvider
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "llama-3.3-70b-versatile"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="agent_model_configs")
