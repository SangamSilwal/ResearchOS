"""
Turns a user's saved AgentModelConfig + UserApiKey rows into the
core.runtime.RunConfig that gets attached to their run's asyncio Task
(see web/run_manager.py). This is the only place decrypted API keys
exist outside the crypto module itself, and they never leave this
process -- they're passed straight into an LLM client constructor.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.runtime import RunConfig
from web import crypto
from web.model_defaults import AGENT_ROLE_SETTINGS_FIELD, DEFAULT_AGENT_MODELS
from web.models import AgentModelConfig, User, UserApiKey


async def build_run_config(db: AsyncSession, user: User) -> RunConfig:
    result = await db.execute(
        select(AgentModelConfig).where(AgentModelConfig.user_id == user.id)
    )
    configured = {row.agent_role: row for row in result.scalars().all()}

    models: dict[str, str] = {}
    for role, settings_field in AGENT_ROLE_SETTINGS_FIELD.items():
        row = configured.get(role.value)
        if row:
            models[settings_field] = f"{row.provider}/{row.model_name}"
        # else: leave unset -- core.runtime.resolve_model() falls back
        # to core.config.settings' own default for that field.

    result = await db.execute(
        select(UserApiKey).where(UserApiKey.user_id == user.id)
    )
    keys: dict[str, str] = {}
    for row in result.scalars().all():
        keys[row.provider] = crypto.decrypt(row.nonce, row.encrypted_key)

    return RunConfig(models=models, keys=keys)


async def account_status(db: AsyncSession, user: User) -> tuple[list[str], list[str], bool]:
    """Returns (configured_providers, missing_providers, using_defaults)."""
    result = await db.execute(select(UserApiKey.provider).where(UserApiKey.user_id == user.id))
    configured_providers = sorted({row for row in result.scalars().all()})

    result = await db.execute(select(AgentModelConfig).where(AgentModelConfig.user_id == user.id))
    agent_configs = result.scalars().all()
    using_defaults = len(agent_configs) == 0

    referenced_providers = {row.provider for row in agent_configs if row.provider != "groq"}
    missing_providers = sorted(referenced_providers - set(configured_providers))

    return configured_providers, missing_providers, using_defaults


def default_agent_models_view() -> list[dict]:
    """Used by GET /api/settings/agent-models to show defaults alongside overrides."""
    out = []
    for role, model_key in DEFAULT_AGENT_MODELS.items():
        provider, model_name = model_key.split("/", 1)
        out.append({
            "agent_role": role.value,
            "provider": provider,
            "model_name": model_name,
            "is_default": True,
        })
    return out
