"""
FastAPI web interface for ResearchOS.

Run it with:  python serve.py
(or:          uvicorn web.app:app --host 0.0.0.0 --port 8080)

Flow: first visit -> create the single login account -> configure API
keys + per-agent models -> submit goals and watch the multi-agent run
live, the same pipeline run.py drives from the CLI.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from core.config import settings
from core.memory import get_recent_runs
from web import config_store, security
from web.mcp_manager import mcp_manager
from web.run_manager import run_manager

TEMPLATES_DIR = __import__("pathlib").Path(__file__).parent / "templates"
STATIC_DIR = __import__("pathlib").Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    mcp_manager.start_all()
    try:
        yield
    finally:
        mcp_manager.stop_all()


app = FastAPI(title="ResearchOS", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key or "dev-secret-key")


def render(request: Request, template: str, **ctx):
    ctx.setdefault("show_nav", security.account_exists() and security.is_logged_in(request))
    ctx.setdefault("error", None)
    ctx.setdefault("notice", None)
    return templates.TemplateResponse(request, template, ctx)


# ---------------------------------------------------------------- account

@app.get("/setup-account")
async def setup_account_form(request: Request):
    if security.account_exists():
        return RedirectResponse("/login", status_code=303)
    return render(request, "setup_account.html")


@app.post("/setup-account")
async def setup_account_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if security.account_exists():
        return RedirectResponse("/login", status_code=303)

    username = username.strip()
    if not username or len(password) < 6:
        return render(
            request, "setup_account.html",
            error="Username required and password must be at least 6 characters.",
        )
    if password != confirm_password:
        return render(request, "setup_account.html", error="Passwords do not match.")

    config_store.apply_values({
        "web_username": username,
        "web_password_hash": security.hash_password(password),
    })
    security.log_in(request)
    return RedirectResponse("/settings", status_code=303)


@app.get("/login")
async def login_form(request: Request):
    if not security.account_exists():
        return RedirectResponse("/setup-account", status_code=303)
    if security.is_logged_in(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html")


@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if (
        username.strip() == settings.web_username
        and security.verify_password(password, settings.web_password_hash)
    ):
        security.log_in(request)
        if not config_store.is_configured():
            return RedirectResponse("/settings", status_code=303)
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", error="Invalid username or password.")


@app.get("/logout")
async def logout(request: Request):
    security.log_out(request)
    return RedirectResponse("/login", status_code=303)


# --------------------------------------------------------------- settings

@app.get("/settings")
async def settings_form(request: Request):
    redirect = security.guard(request)
    if redirect:
        return redirect
    return render(
        request, "settings.html",
        values=config_store.current_form_values(),
        agent_labels=config_store.AGENT_FIELD_LABELS,
        suggestions=config_store.MODEL_SUGGESTIONS,
        missing_keys=config_store.missing_provider_keys(),
    )


@app.post("/settings")
async def settings_submit(request: Request):
    redirect = security.guard(request)
    if redirect:
        return redirect

    form = await request.form()
    fields = {**config_store.PROVIDER_KEY_FIELDS, **config_store.AGENT_MODEL_FIELDS}
    values = {field: (form.get(field) or "").strip() for field in fields}
    config_store.apply_values(values)
    mcp_manager.restart_web_search()

    return render(
        request, "settings.html",
        values=config_store.current_form_values(),
        agent_labels=config_store.AGENT_FIELD_LABELS,
        suggestions=config_store.MODEL_SUGGESTIONS,
        missing_keys=config_store.missing_provider_keys(),
        notice="Configuration saved.",
    )


# -------------------------------------------------------------- dashboard

@app.get("/")
async def dashboard(request: Request):
    redirect = security.guard(request)
    if redirect:
        return redirect
    if not config_store.is_configured():
        return RedirectResponse("/settings", status_code=303)

    recent_runs = await get_recent_runs(n=20)
    return render(request, "dashboard.html", recent_runs=recent_runs)


@app.post("/runs")
async def start_run(request: Request, goal: str = Form(...), project_id: str = Form("")):
    redirect = security.guard(request)
    if redirect:
        return redirect
    if not config_store.is_configured():
        return RedirectResponse("/settings", status_code=303)

    goal = goal.strip()
    if not goal:
        return RedirectResponse("/", status_code=303)

    run_id = run_manager.start_run(goal, project_id.strip() or None)
    return RedirectResponse(f"/run/{run_id}", status_code=303)


@app.get("/run/{run_id}")
async def run_detail(request: Request, run_id: str):
    redirect = security.guard(request)
    if redirect:
        return redirect

    result = run_manager.get_result(run_id)
    if result is not None:
        goal = result.get("goal", "")
        live = result.get("status") == "running"
        result_ctx = result if result.get("status") != "running" else None
    else:
        # Not an in-memory run from this process (e.g. server restarted,
        # or it was kicked off from the CLI) -- fall back to persisted
        # run memory for a static summary.
        past_runs = await get_recent_runs(n=200)
        match = next((r for r in past_runs if r["project_id"] == run_id), None)
        if match is None:
            return RedirectResponse("/", status_code=303)
        goal = match["goal"]
        live = False
        result_ctx = {
            "status": "done",
            "summary": match.get("summary"),
            "tasks_by_status": match.get("task_summary", {}),
            "files_written": match.get("files_written", []),
            "flagged": [{"title": t, "output_path": "", "feedback": ""} for t in match.get("flagged_tasks", [])],
            "competition": None,
        }

    return render(
        request, "run.html",
        run_id=run_id, goal=goal, live=live, result=result_ctx, initial_log=[],
    )


@app.get("/run/{run_id}/events")
async def run_events(request: Request, run_id: str):
    redirect = security.guard(request)
    if redirect:
        return redirect

    queue = run_manager.get_queue(run_id)
    if queue is None:
        return RedirectResponse(f"/run/{run_id}", status_code=303)

    async def event_stream():
        while True:
            item = await queue.get()
            if item is None:
                yield "event: end\ndata: {}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
