"""
Execute the LangGraph agent pipeline for a web Run.

Loads the run from Postgres, resolves the user's model config, streams
agent output into run_events, and on success creates a zip + assistant message.
"""
from __future__ import annotations

import bootstrap  # noqa: F401

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.memory import save_run_memory
from database import AsyncSessionLocal
from model_apply import apply_resolved_models
from model_resolver import MissingApiKeyError, resolve_all_roles
from models import Message, Run, RunEvent, Thread
from run_type import detect_run_type_from_tasks, infer_run_type
from zip_builder import build_project_zip


async def _add_event(
    db: AsyncSession,
    run_id: uuid.UUID,
    *,
    content: str,
    event_type: str,
    agent: str | None = None,
) -> None:
    db.add(
        RunEvent(
            run_id=run_id,
            agent=agent,
            content=content,
            event_type=event_type,
        )
    )
    await db.commit()


async def execute_run(run_id: uuid.UUID, celery_task_id: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Run)
            .options(selectinload(Run.thread).selectinload(Thread.user))
            .where(Run.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            return

        if celery_task_id:
            run.celery_task_id = celery_task_id

        run.status = "running"
        await db.commit()

        user_id = run.thread.user_id
        project_id = str(run.id)
        output_root = os.path.join(settings.output_dir, project_id)

        try:
            resolved = await resolve_all_roles(db, user_id)
            apply_resolved_models(resolved)
        except MissingApiKeyError as exc:
            run.status = "error"
            run.completed_at = datetime.now(timezone.utc)
            await _add_event(
                db, run.id,
                content=str(exc),
                event_type="agent_message",
                agent="system",
            )
            await db.commit()
            return

        if run.type not in ("build", "research"):
            run.type = infer_run_type(run.goal)
            await db.commit()

        from agents.graph import build_graph
        from agents.state import ResearchState

        state: ResearchState = {
            "goal": run.goal,
            "messages": [],
            "tasks": [],
            "research_findings": [],
            "output": {},
            "summary": None,
            "next_agent": "orchestrator",
            "error": None,
            "project_id": project_id,
        }

        compiled = build_graph()
        final_state: dict[str, Any] | None = None

        try:
            async for event in compiled.astream(state, stream_mode="values"):
                final_state = event
                messages = event.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    content = getattr(last_msg, "content", str(last_msg))
                    agent = event.get("next_agent") or "agent"
                    await _add_event(
                        db, run.id,
                        content=content,
                        event_type="agent_message",
                        agent=agent,
                    )

            if final_state is None:
                raise RuntimeError("Graph produced no output.")

            if final_state.get("error"):
                raise RuntimeError(final_state["error"])

            tasks = final_state.get("tasks", [])
            detected_type = detect_run_type_from_tasks(tasks)
            if run.type != detected_type:
                run.type = detected_type

            by_status: dict[str, int] = {}
            for t in tasks:
                status = t.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

            written = [t.get("output_path") for t in tasks if t.get("output_path")]
            flagged = [t for t in tasks if t.get("status") == "flagged"]
            summary_text = final_state.get("summary") or ""

            run.task_summary = by_status
            run.flagged_tasks = [t.get("title", "") for t in flagged]
            run.status = "done"
            run.completed_at = datetime.now(timezone.utc)

            if run.type == "build" and os.path.isdir(output_root):
                zip_dir = os.environ.get("RUN_ZIP_DIR", os.path.join(settings.output_dir, "_zips"))
                zip_path = os.path.join(zip_dir, f"{run.id}.zip")
                run.zip_path = build_project_zip(output_root, zip_path)

            assistant_message = Message(
                thread_id=run.thread_id,
                role="assistant",
                content=summary_text or "Run completed.",
            )
            db.add(assistant_message)
            await db.flush()
            run.message_id = assistant_message.id

            run.thread.updated_at = datetime.now(timezone.utc)

            await save_run_memory(
                project_id=project_id,
                goal=run.goal,
                files=[p for p in written if p],
                flagged=run.flagged_tasks or [],
                task_summary=by_status,
                summary=summary_text,
            )

            await db.commit()

        except Exception as exc:
            await db.rollback()
            result = await db.execute(select(Run).where(Run.id == run_id))
            run = result.scalar_one()
            run.status = "error"
            run.completed_at = datetime.now(timezone.utc)
            await _add_event(
                db, run.id,
                content=f"Pipeline failed: {exc}",
                event_type="agent_message",
                agent="system",
            )
            await db.commit()
            raise
