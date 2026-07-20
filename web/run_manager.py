"""
Drives agents.graph.build_graph() in the background for a specific
user's run. Unlike the single-operator prototype, every run:

- is attached to that user's resolved model/API-key config via
  core.runtime.set_run_config(), scoped to this run's own asyncio Task
  so concurrent users' runs never see each other's keys (see
  core/runtime.py's docstring for why that's safe)
- is persisted as a Run row (+ Thread/Message it belongs to, + one
  RunEvent row per streamed message) so history survives a restart,
  unlike the prototype's in-memory-only results
- gets its coder output zipped for download if it wrote any files
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from agents.graph import build_graph
from agents.state import ResearchState
from core.memory import get_recent_runs, save_run_memory
from core.runtime import RunConfig, reset_run_config, set_run_config
from web.config_resolution import build_run_config
from web.database import AsyncSessionLocal
from web.models import Message, MessageRole, Run, RunEvent, RunEventType, RunStatus, RunType, Thread, User
from web.zip_utils import zip_run_output


class RunManager:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    async def start_run(self, user: User, goal: str, thread_id: uuid.UUID | None) -> Run:
        async with AsyncSessionLocal() as db:
            thread = None
            if thread_id is not None:
                result = await db.execute(
                    select(Thread).where(Thread.id == thread_id, Thread.user_id == user.id)
                )
                thread = result.scalar_one_or_none()
                if thread is None:
                    raise ValueError("Thread not found")

            if thread is None:
                thread = Thread(user_id=user.id, title=goal[:80])
                db.add(thread)
                await db.flush()

            message = Message(thread_id=thread.id, role=MessageRole.user.value, content=goal)
            db.add(message)
            await db.flush()

            run = Run(
                thread_id=thread.id,
                message_id=message.id,
                goal=goal,
                type=RunType.build.value,  # refined once the orchestrator's task list is known
                status=RunStatus.queued.value,
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)

            run_config = await build_run_config(db, user)

        queue: asyncio.Queue = asyncio.Queue()
        self._queues[str(run.id)] = queue
        asyncio.create_task(self._execute(run.id, goal, run_config))
        return run

    async def _execute(self, run_id: uuid.UUID, goal: str, run_config: RunConfig) -> None:
        queue = self._queues[str(run_id)]
        token = set_run_config(run_config)

        async def emit(text: str, agent: str | None = None) -> None:
            await queue.put({"type": "log", "agent": agent, "text": text})
            async with AsyncSessionLocal() as db:
                db.add(RunEvent(
                    run_id=run_id, agent=agent, content=text,
                    event_type=RunEventType.agent_message.value,
                ))
                await db.commit()

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Run).where(Run.id == run_id))
                run = result.scalar_one()
                run.status = RunStatus.running.value
                await db.commit()

            recent_runs = await get_recent_runs(n=3)
            if recent_runs:
                await emit(f"Loaded memory from {len(recent_runs)} previous run(s).")

            state: ResearchState = {
                "goal": goal,
                "messages": [],
                "tasks": [],
                "research_findings": [],
                "output": {},
                "summary": None,
                "next_agent": "orchestrator",
                "error": None,
                "project_id": str(run_id),
            }

            await emit(f"Goal: {goal}")
            compiled_graph = build_graph()

            final_state: dict = {}
            async for event in compiled_graph.astream(state, stream_mode="values"):
                final_state = event
                messages = event.get("messages", [])
                if messages:
                    await emit(str(messages[-1].content))

            summary_text = final_state.get("summary")
            tasks = final_state.get("tasks", [])

            by_status: dict[str, int] = {}
            for t in tasks:
                status = t.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

            written = [t.get("output_path") for t in tasks if t.get("output_path")]
            flagged = [t for t in tasks if t.get("status") == "flagged"]
            run_type = (
                RunType.build.value
                if any(t.get("agent") in ("architect", "coder") for t in tasks)
                else RunType.research.value
            )

            zip_path = zip_run_output(str(run_id)) if written else None

            await save_run_memory(
                project_id=str(run_id),
                goal=goal,
                files=written,
                flagged=[t.get("title", "") for t in flagged],
                task_summary=by_status,
                summary=summary_text or "",
            )

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Run).where(Run.id == run_id))
                run = result.scalar_one()
                run.status = RunStatus.done.value
                run.type = run_type
                run.summary = summary_text
                run.task_summary = by_status
                run.flagged_tasks = [
                    {
                        "title": t.get("title"),
                        "output_path": t.get("output_path"),
                        "feedback": (t.get("critic_verdict") or {}).get("feedback", ""),
                    }
                    for t in flagged
                ]
                run.zip_path = zip_path
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()

            await queue.put({"type": "done", "run_id": str(run_id)})
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Run).where(Run.id == run_id))
                run = result.scalar_one_or_none()
                if run is not None:
                    run.status = RunStatus.error.value
                    run.error = error_text
                    run.completed_at = datetime.now(timezone.utc)
                    db.add(RunEvent(
                        run_id=run_id, agent=None, content=error_text,
                        event_type=RunEventType.error.value,
                    ))
                    await db.commit()
            await queue.put({"type": "error", "text": error_text})
        finally:
            reset_run_config(token)
            await queue.put(None)  # sentinel: closes the SSE stream
            self._queues.pop(str(run_id), None)

    def get_queue(self, run_id: str) -> asyncio.Queue | None:
        return self._queues.get(run_id)


run_manager = RunManager()
