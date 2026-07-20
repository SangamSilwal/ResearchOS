from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------- auth

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ------------------------------------------------------------ settings

class ApiKeyIn(BaseModel):
    api_key: str = Field(min_length=1)
    label: Optional[str] = None


class ApiKeyOut(BaseModel):
    provider: str
    label: Optional[str] = None
    last_used_at: Optional[datetime] = None
    updated_at: datetime


class AgentModelIn(BaseModel):
    # "provider/model-name", e.g. "gemini/gemini-2.5-flash"
    model: str = Field(min_length=1)


class AgentModelsIn(BaseModel):
    orchestrator: Optional[str] = None
    researcher: Optional[str] = None
    architect_a: Optional[str] = None
    architect_b: Optional[str] = None
    judge: Optional[str] = None
    planner: Optional[str] = None
    coder: Optional[str] = None
    critic: Optional[str] = None
    summarizer: Optional[str] = None


class AgentModelOut(BaseModel):
    agent_role: str
    provider: str
    model_name: str
    is_default: bool  # true if this is the platform default, not a user override


class AccountStatus(BaseModel):
    configured_providers: list[str]
    missing_providers: list[str]  # providers referenced by a custom agent model but with no key saved
    using_defaults: bool          # true if the account has no custom agent models at all yet


# ----------------------------------------------------------------- runs

class RunCreate(BaseModel):
    goal: str = Field(min_length=1)
    thread_id: Optional[uuid.UUID] = None
    run_type: Optional[str] = None  # "build" | "research"; auto-detected by the orchestrator if omitted


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    goal: str
    type: str
    status: str
    summary: Optional[str] = None
    task_summary: Optional[dict[str, Any]] = None
    flagged_tasks: Optional[Any] = None
    error: Optional[str] = None
    has_download: bool = False
    created_at: datetime
    completed_at: Optional[datetime] = None


class RunEventOut(BaseModel):
    agent: Optional[str] = None
    content: str
    event_type: str
    created_at: datetime
