from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from web.database import get_db
from web.models import User
from web.oauth import SUPPORTED_OAUTH_PROVIDERS, oauth
from web.schemas import TokenResponse, UserOut
from web.security import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request):
    if provider not in SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(404, f"Unknown provider '{provider}'. Supported: {SUPPORTED_OAUTH_PROVIDERS}")
    client = oauth.create_client(provider)
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/{provider}/callback"
    return await client.authorize_redirect(request, redirect_uri)


async def _google_profile(client, token) -> dict:
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await client.userinfo(token=token)
    return {
        "email": userinfo["email"],
        "name": userinfo.get("name"),
        "avatar_url": userinfo.get("picture"),
        "provider_id": userinfo["sub"],
    }


async def _github_profile(client, token) -> dict:
    profile_resp = await client.get("user", token=token)
    profile = profile_resp.json()

    email = profile.get("email")
    if not email:
        emails_resp = await client.get("user/emails", token=token)
        emails = emails_resp.json()
        primary = next((e["email"] for e in emails if e.get("primary")), None)
        email = primary or (emails[0]["email"] if emails else None)

    if not email:
        raise HTTPException(400, "GitHub account has no accessible email address")

    return {
        "email": email,
        "name": profile.get("name") or profile.get("login"),
        "avatar_url": profile.get("avatar_url"),
        "provider_id": str(profile["id"]),
    }


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    if provider not in SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(404, f"Unknown provider '{provider}'")

    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)

    if provider == "google":
        profile = await _google_profile(client, token)
    else:
        profile = await _github_profile(client, token)

    result = await db.execute(
        select(User).where(User.provider == provider, User.provider_id == profile["provider_id"])
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=profile["email"],
            name=profile["name"],
            avatar_url=profile["avatar_url"],
            provider=provider,
            provider_id=profile["provider_id"],
        )
        db.add(user)
    else:
        user.email = profile["email"]
        user.name = profile["name"]
        user.avatar_url = profile["avatar_url"]

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id)

    if settings.frontend_url:
        return RedirectResponse(f"{settings.frontend_url}?token={access_token}")

    # No frontend configured yet -- hand the token back directly so the
    # API is fully usable (e.g. via Swagger's "Authorize" button or curl)
    # without one.
    return TokenResponse(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user
