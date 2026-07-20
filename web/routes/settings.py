from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.runtime import SUPPORTED_PROVIDERS
from web import config_resolution, crypto
from web.database import get_db
from web.model_defaults import DEFAULT_AGENT_MODELS
from web.models import AgentModelConfig, AgentRole, LLMProvider, User, UserApiKey
from web.schemas import (
    AccountStatus,
    AgentModelOut,
    AgentModelsIn,
    ApiKeyIn,
    ApiKeyOut,
)
from web.security import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])

BYO_PROVIDERS = {p.value for p in LLMProvider}  # gemini, mistral, openrouter


@router.get("/status", response_model=AccountStatus)
async def get_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    configured, missing, using_defaults = await config_resolution.account_status(db, current_user)
    return AccountStatus(
        configured_providers=configured,
        missing_providers=missing,
        using_defaults=using_defaults,
    )


# ------------------------------------------------------------- API keys

@router.get("/keys", response_model=list[ApiKeyOut])
async def list_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserApiKey).where(UserApiKey.user_id == current_user.id))
    return [
        ApiKeyOut(
            provider=row.provider,
            label=row.label,
            last_used_at=row.last_used_at,
            updated_at=row.updated_at,
        )
        for row in result.scalars().all()
    ]


@router.put("/keys/{provider}", response_model=ApiKeyOut, status_code=200)
async def upsert_key(
    provider: str,
    body: ApiKeyIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if provider not in BYO_PROVIDERS:
        raise HTTPException(
            400,
            f"'{provider}' is not a bring-your-own-key provider. "
            f"Supported: {sorted(BYO_PROVIDERS)}. "
            f"'groq' uses the platform's own key and never needs one from you.",
        )

    nonce, ciphertext = crypto.encrypt(body.api_key)

    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == current_user.id, UserApiKey.provider == provider
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserApiKey(
            user_id=current_user.id, provider=provider,
            encrypted_key=ciphertext, nonce=nonce, label=body.label,
        )
        db.add(row)
    else:
        row.encrypted_key = ciphertext
        row.nonce = nonce
        row.label = body.label

    await db.commit()
    await db.refresh(row)
    return ApiKeyOut(
        provider=row.provider, label=row.label,
        last_used_at=row.last_used_at, updated_at=row.updated_at,
    )


@router.delete("/keys/{provider}", status_code=204)
async def delete_key(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == current_user.id, UserApiKey.provider == provider
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(404, f"No key saved for provider '{provider}'")
    await db.delete(row)
    await db.commit()


# --------------------------------------------------------- agent models

@router.get("/agent-models", response_model=list[AgentModelOut])
async def get_agent_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentModelConfig).where(AgentModelConfig.user_id == current_user.id)
    )
    overrides = {row.agent_role: row for row in result.scalars().all()}

    out = []
    for role, model_key in DEFAULT_AGENT_MODELS.items():
        row = overrides.get(role.value)
        if row:
            out.append(AgentModelOut(
                agent_role=role.value, provider=row.provider,
                model_name=row.model_name, is_default=False,
            ))
        else:
            provider, model_name = model_key.split("/", 1)
            out.append(AgentModelOut(
                agent_role=role.value, provider=provider,
                model_name=model_name, is_default=True,
            ))
    return out


@router.put("/agent-models", response_model=list[AgentModelOut])
async def set_agent_models(
    body: AgentModelsIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No agent model fields provided")

    valid_roles = {r.value for r in AgentRole}
    for role, model_key in updates.items():
        if role not in valid_roles:
            raise HTTPException(400, f"Unknown agent role '{role}'")
        if "/" not in model_key:
            raise HTTPException(400, f"'{model_key}' must be in 'provider/model-name' format")
        provider = model_key.split("/", 1)[0]
        if provider not in SUPPORTED_PROVIDERS:
            raise HTTPException(
                400,
                f"Unsupported provider '{provider}' for role '{role}'. "
                f"Supported: {list(SUPPORTED_PROVIDERS)}",
            )

    for role, model_key in updates.items():
        provider, model_name = model_key.split("/", 1)
        result = await db.execute(
            select(AgentModelConfig).where(
                AgentModelConfig.user_id == current_user.id,
                AgentModelConfig.agent_role == role,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            db.add(AgentModelConfig(
                user_id=current_user.id, agent_role=role,
                provider=provider, model_name=model_name,
            ))
        else:
            row.provider = provider
            row.model_name = model_name

    await db.commit()
    return await get_agent_models(current_user=current_user, db=db)
