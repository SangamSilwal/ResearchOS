import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from crypto import encrypt_secret
from database import get_db
from dependencies import get_current_user
from model_defaults import DEFAULT_AGENT_MODELS
from model_resolver import has_key_for_role_config
from models import AgentModelConfig, AgentRole, LLMProvider, User, UserApiKey
from schemas import ApiKeyIn, ApiKeyOut, AgentModelConfigIn, EffectiveModelOut

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/keys", response_model=list[ApiKeyOut])
async def list_keys(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(select(UserApiKey).where(UserApiKey.user_id == user.id))
    return result.scalars().all()

@router.put("/keys", response_model=ApiKeyOut)
async def upsert_key(
    payload: ApiKeyIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.provider == LLMProvider.anthropic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anthropic is the system default and doesn't take a user-supplied key.",
        )

    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == user.id, UserApiKey.provider == payload.provider.value
        )
    )
    existing = result.scalar_one_or_none()
    ciphertext, nonce = encrypt_secret(payload.api_key)
    if existing:
        existing.encrypted_key = ciphertext
        existing.nonce = nonce
        existing.label = payload.label
        key_row = existing
    else:
        key_row = UserApiKey(
            user_id=user.id,
            provider=payload.provider.value,
            encrypted_key=ciphertext,
            nonce=nonce,
            label=payload.label,
        )
        db.add(key_row)
    await db.commit()
    await db.refresh(key_row)
    return key_row


@router.delete("/keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    provider: LLMProvider,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == user.id, UserApiKey.provider == provider.value
        )
    )
    key_row = result.scalar_one_or_none()
    if key_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No key on file for that provider.")

    dependent = await db.execute(
        select(AgentModelConfig.agent_role).where(
            AgentModelConfig.user_id == user.id, AgentModelConfig.provider == provider.value
        )
    )
    dependent_roles = [r for (r,) in dependent.all()]
    if dependent_roles:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Roles still configured to use '{provider.value}': {dependent_roles}. "
                "Reassign or remove those role configs first."
            ),
        )

    await db.delete(key_row)
    await db.commit()


@router.get("/models", response_model=list[EffectiveModelOut])
async def list_effective_models(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(AgentModelConfig).where(AgentModelConfig.user_id == user.id)
    )
    overrides = {AgentRole(c.agent_role): c for c in result.scalars().all()}

    out: list[EffectiveModelOut] = []
    for role in AgentRole:
        config = overrides.get(role)
        if config is None:
            provider, model_name = DEFAULT_AGENT_MODELS[role]
            out.append(EffectiveModelOut(
                agent_role=role, provider=provider, model_name=model_name,
                source="default", has_required_key=True,
            ))
        else:
            has_key = await has_key_for_role_config(db, user.id, config)
            out.append(EffectiveModelOut(
                agent_role=role, provider=LLMProvider(config.provider),
                model_name=config.model_name, source="user", has_required_key=has_key,
            ))
    return out


@router.put("/models/{agent_role}", response_model=EffectiveModelOut)
async def set_role_model(
    agent_role: AgentRole,
    payload: AgentModelConfigIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentModelConfig).where(
            AgentModelConfig.user_id == user.id, AgentModelConfig.agent_role == agent_role.value
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.provider = payload.provider.value
        existing.model_name = payload.model_name
        config = existing
    else:
        config = AgentModelConfig(
            user_id=user.id, agent_role=agent_role.value,
            provider=payload.provider.value, model_name=payload.model_name,
        )
        db.add(config)
    await db.commit()
    await db.refresh(config)
    has_key = await has_key_for_role_config(db, user.id, config)
    return EffectiveModelOut(
        agent_role=agent_role, provider=payload.provider, model_name=payload.model_name,
        source="user", has_required_key=has_key,
    )


@router.delete("/models/{agent_role}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_role_model(
    agent_role: AgentRole,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Revert a role back to the system default by removing the override."""
    result = await db.execute(
        select(AgentModelConfig).where(
            AgentModelConfig.user_id == user.id, AgentModelConfig.agent_role == agent_role.value
        )
    )
    config = result.scalar_one_or_none()
    if config is None:
        return  
    await db.delete(config)
    await db.commit()