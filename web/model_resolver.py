"""
Resolves, for a given user and pipeline role, which provider + model to
call and (for BYO providers) the decrypted API key to use.

Resolution order per role:
    1. AgentModelConfig row for (user, role), if one exists
       - provider == anthropic  -> use the platform's own ANTHROPIC_API_KEY
       - provider == BYO        -> look up + decrypt the user's UserApiKey
                                    for that provider; raise if missing
    2. Otherwise -> DEFAULT_AGENT_MODELS[role] (always anthropic/system key)

Decryption happens here and only here, right before a run needs to
actually call the provider — never eagerly, never logged, never sent
back to the frontend.
"""
import os
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto import decrypt_secret
from model_defaults import DEFAULT_AGENT_MODELS
from models import AgentModelConfig, AgentRole, LLMProvider, UserApiKey


class MissingApiKeyError(RuntimeError):
    """Raised when a role is configured for a BYO provider the user has no key for."""
    def __init__(self, provider: LLMProvider, agent_role: AgentRole):
        self.provider = provider
        self.agent_role = agent_role
        super().__init__(
            f"No API key on file for provider '{provider.value}', required by the "
            f"'{agent_role.value}' role. Add one in Settings before starting a run."
        )


@dataclass
class ResolvedModel:
    agent_role: AgentRole
    provider: LLMProvider
    model_name: str
    api_key: str | None  # None for provider == anthropic (uses system key)
    source: str = "default"  # "user" | "default", set by callers that need it


async def resolve_role(
    db: AsyncSession, user_id: uuid.UUID, agent_role: AgentRole
) -> ResolvedModel:
    result = await db.execute(
        select(AgentModelConfig).where(
            AgentModelConfig.user_id == user_id,
            AgentModelConfig.agent_role == agent_role.value,
        )
    )
    config = result.scalar_one_or_none()

    if config is None:
        provider, model_name = DEFAULT_AGENT_MODELS[agent_role]
        return ResolvedModel(agent_role, provider, model_name, api_key=None, source="default")

    provider = LLMProvider(config.provider)

    if provider == LLMProvider.anthropic:
        return ResolvedModel(agent_role, provider, config.model_name, api_key=None, source="user")

    key_result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider.value,
        )
    )
    key_row = key_result.scalar_one_or_none()
    if key_row is None:
        raise MissingApiKeyError(provider, agent_role)

    decrypted = decrypt_secret(key_row.encrypted_key, key_row.nonce)
    return ResolvedModel(agent_role, provider, config.model_name, api_key=decrypted, source="user")


async def resolve_all_roles(
    db: AsyncSession, user_id: uuid.UUID
) -> dict[AgentRole, ResolvedModel]:
    """
    Called once at the start of a run to build the full per-role model
    map handed to the LangGraph pipeline. Raises MissingApiKeyError
    immediately (before any agent runs) if any configured role is
    missing its key — fail fast rather than partway through a pipeline.
    """
    return {role: await resolve_role(db, user_id, role) for role in AgentRole}


async def has_key_for_role_config(db: AsyncSession, user_id: uuid.UUID, config: AgentModelConfig) -> bool:
    """Used by the /api/config/models endpoint to flag missing-key rows in the UI."""
    provider = LLMProvider(config.provider)
    if provider == LLMProvider.anthropic:
        return True
    result = await db.execute(
        select(UserApiKey.id).where(
            UserApiKey.user_id == user_id, UserApiKey.provider == provider.value
        )
    )
    return result.scalar_one_or_none() is not None


def system_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set on the server.")
    return key