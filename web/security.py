"""
Minimal single-operator auth for the web UI.

There is exactly one account, created on first visit ("setup-account"),
stored as a salted hash in .env via web/config_store.py. After that, every
request needs a valid signed session cookie to reach anything except the
login page.
"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import Request
from starlette.responses import RedirectResponse

from core.config import settings


def hash_password(password: str) -> str:
    # Not meant to withstand a stolen-database attack at scale -- this is
    # a single-operator local/self-hosted tool. Salting with the app's
    # secret_key is enough to stop plain rainbow-table lookups.
    salted = f"{settings.secret_key}:{password}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def account_exists() -> bool:
    return bool(settings.web_username and settings.web_password_hash)


def is_logged_in(request: Request) -> bool:
    return bool(account_exists() and request.session.get("user") == settings.web_username)


def log_in(request: Request) -> None:
    request.session["user"] = settings.web_username


def log_out(request: Request) -> None:
    request.session.clear()


def guard(request: Request):
    """
    Call at the top of a protected route. Returns a RedirectResponse if
    the request should be bounced somewhere else, or None if it's fine to
    proceed.
    """
    if not account_exists():
        return RedirectResponse("/setup-account", status_code=303)
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=303)
    return None
