import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from models import AgentRole, LLMProvider


# ---------------------------------------------------------------------------
# users / auth
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    provider: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# threads / messages
# ---------------------------------------------------------------------------

class ThreadCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class ThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ThreadDetailOut(ThreadOut):
    messages: list[MessageOut] = []


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------

class RunCreate(BaseModel):
    thread_id: uuid.UUID
    goal: str = Field(min_length=1, max_length=10000)
    type: Optional[str] = Field(
        default=None,
        description="build | research — omit to auto-detect from the goal",
    )


class RunEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    agent: Optional[str]
    content: str
    event_type: str
    created_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    goal: str
    type: str
    status: str
    zip_path: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class RunDetailOut(RunOut):
    events: list[RunEventOut] = []


# ---------------------------------------------------------------------------
# BYO API keys — never return the decrypted key, ever
# ---------------------------------------------------------------------------

class ApiKeyIn(BaseModel):
    provider: LLMProvider
    api_key: str = Field(min_length=8, description="Plaintext key, encrypted before storage")
    label: Optional[str] = Field(default=None, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider": "openrouter",
                "api_key": "sk-or-v1-...",
                "label": "personal OpenRouter key",
            }
        }
    )


class ApiKeyOut(BaseModel):
    """Metadata only — the encrypted key material never leaves the server."""
    model_config = ConfigDict(from_attributes=True)

    provider: str
    label: Optional[str]
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# per-role model configuration
# ---------------------------------------------------------------------------

class AgentModelConfigIn(BaseModel):
    provider: LLMProvider
    model_name: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"provider": "mistral", "model_name": "mistral-large-latest"}
        }
    )


class EffectiveModelOut(BaseModel):
    """
    What a role will actually use right now — either the user's override
    or the system default, with `source` telling you which.
    """
    agent_role: AgentRole
    provider: LLMProvider
    model_name: str
    source: str  # "user" | "default"
    has_required_key: bool  # False if provider is BYO and no key is on file yet