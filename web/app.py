"""
ResearchOS web API (FastAPI, JSON only -- no server-rendered pages).
A frontend (React/Next.js) is expected to be built against this
separately; see README.md's "Web API" section for the endpoint summary.

Run it with:  python serve.py
(or:          uvicorn web.app:app --host 0.0.0.0 --port 8080)
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Populate os.environ from .env before anything else imports settings --
# core.memory's raw asyncpg path and the MCP subprocess spawns both read
# os.environ directly rather than through core.config.settings.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from core.config import settings
from web.mcp_manager import mcp_manager
from web.routes import auth, runs, settings as settings_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    mcp_manager.start_all()
    try:
        yield
    finally:
        mcp_manager.stop_all()


app = FastAPI(title="ResearchOS API", lifespan=lifespan)

# Only used transiently during the OAuth login handshake (Authlib stores
# state/nonce here) -- actual API auth is the JWT bearer token issued at
# the end of that handshake, not this cookie. See web/routes/auth.py.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "dev-secret-key",
    same_site="lax",   # works fine for same-site-ish localhost dev
    https_only=False,
)

_allow_origins = [settings.frontend_url] if settings.frontend_url else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(settings_routes.router)
app.include_router(runs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
