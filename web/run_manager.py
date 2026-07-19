"""
Drives agents.graph.build_graph() in the background for the web UI.

This mirrors run.py's console loop, but pushes each step into an
asyncio.Queue per run so a browser tab can subscribe to it over
Server-Sent Events instead of reading stdout.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from agents.graph import build_graph
from agents.state import ResearchState
from core.memory import get_recent_runs, save_run_memory


class RunManager:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._results: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []

    def start_run(self, goal: str, project_id: str | None = None) -> str:
        run_id = (project_id or "").strip() or f"web_{uuid.uuid4().hex[:8]}"
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[run_id] = queue
        self._results[run_id] = {
            "status": "running",
            "goal": goal,
            "started_at": time.time(),
        }
        self._order.insert(0, run_id)
        asyncio.create_task(self._execute(run_id, goal))
        return run_id

    async def _execute(self, run_id: str, goal: str) -> None:
        queue = self._queues[run_id]

        async def emit(text: str) -> None:
            await queue.put({"type": "log", "text": text})

        try:
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
                "project_id": run_id,
            }

            await emit(f"Goal: {goal}")
            compiled_graph = build_graph()

            final_state: dict[str, Any] | None = None
            async for event in compiled_graph.astream(state, stream_mode="values"):
                final_state = event
                messages = event.get("messages", [])
                if messages:
                    await emit(str(messages[-1].content))

            final_state = final_state or {}
            summary_text = final_state.get("summary")
            tasks = final_state.get("tasks", [])

            by_status: dict[str, int] = {}
            for t in tasks:
                status = t.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

            written = [t.get("output_path") for t in tasks if t.get("output_path")]
            flagged = [t for t in tasks if t.get("status") == "flagged"]
            competition = final_state.get("architecture_competition", {})

            await save_run_memory(
                project_id=run_id,
                goal=goal,
                files=written,
                flagged=[t.get("title", "") for t in flagged],
                task_summary=by_status,
                summary=summary_text or "",
            )

            result = {
                "status": "done",
                "goal": goal,
                "summary": summary_text,
                "files_written": written,
                "tasks_by_status": by_status,
                "flagged": [
                    {
                        "title": t.get("title"),
                        "output_path": t.get("output_path"),
                        "issues": t.get("critic_verdict", {}).get("issues", []),
                        "feedback": t.get("critic_verdict", {}).get("feedback", ""),
                    }
                    for t in flagged
                ],
                "competition": {
                    "winner": competition.get("winner"),
                    "justification": competition.get("verdict", {}).get("justification", ""),
                } if competition else None,
                "finished_at": time.time(),
            }
            self._results[run_id] = result
            await queue.put({"type": "done", "result": result})
        except Exception as exc:  # surfaced to the UI, run loop must not crash
            result = {
                "status": "error",
                "goal": goal,
                "error": f"{type(exc).__name__}: {exc}",
                "finished_at": time.time(),
            }
            self._results[run_id] = result
            await queue.put({"type": "error", "text": result["error"]})
        finally:
            await queue.put(None)  # sentinel: closes the SSE stream

    def get_queue(self, run_id: str) -> asyncio.Queue | None:
        return self._queues.get(run_id)

    def get_result(self, run_id: str) -> dict[str, Any] | None:
        return self._results.get(run_id)

    def recent_run_ids(self, limit: int = 20) -> list[str]:
        return self._order[:limit]


run_manager = RunManager()
