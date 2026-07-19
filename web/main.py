"""
FastAPI app entrypoint.

Run from web/:
    uvicorn main:app --reload
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.auth import router as auth_router
from api.config import router as config_router
from api.runs import router as runs_router
from api.threads import router as threads_router

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
SESSION_SECRET = os.environ.get("SESSION_SECRET", os.environ.get("JWT_SECRET", ""))

app = FastAPI(title="ResearchOS API")

# Authlib's OAuth redirect flow stores state in the session cookie.
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET or "dev-only-insecure-secret")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(threads_router)
app.include_router(config_router)
app.include_router(runs_router)


@app.get("/health")
async def health():
    return {"status": "ok"} 