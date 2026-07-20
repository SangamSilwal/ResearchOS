from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web.database import get_db
from web.models import Run, RunEvent, Thread, User
from web.run_manager import run_manager
from web.schemas import RunCreate, RunEventOut, RunOut
from web.security import get_current_user

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _to_run_out(run: Run) -> RunOut:
    return RunOut(
        id=run.id, thread_id=run.thread_id, goal=run.goal, type=run.type,
        status=run.status, summary=run.summary, task_summary=run.task_summary,
        flagged_tasks=run.flagged_tasks, error=run.error,
        has_download=bool(run.zip_path), created_at=run.created_at,
        completed_at=run.completed_at,
    )


async def _get_owned_run(run_id: uuid.UUID, user: User, db: AsyncSession) -> Run:
    result = await db.execute(
        select(Run).join(Thread).where(Run.id == run_id, Thread.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(404, "Run not found")
    return run


@router.post("", response_model=RunOut, status_code=201)
async def create_run(
    body: RunCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        run = await run_manager.start_run(current_user, body.goal, body.thread_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return _to_run_out(run)


@router.get("", response_model=list[RunOut])
async def list_runs(
    thread_id: uuid.UUID | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Run).join(Thread).where(Thread.user_id == current_user.id)
    if thread_id is not None:
        query = query.where(Run.thread_id == thread_id)
    query = query.order_by(Run.created_at.desc()).limit(min(limit, 100))
    result = await db.execute(query)
    return [_to_run_out(r) for r in result.scalars().all()]


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await _get_owned_run(run_id, current_user, db)
    return _to_run_out(run)


@router.get("/{run_id}/events", response_model=list[RunEventOut])
async def get_run_events(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persisted event history. For a run still in progress, use the /stream endpoint instead."""
    await _get_owned_run(run_id, current_user, db)
    result = await db.execute(
        select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.created_at)
    )
    return [
        RunEventOut(agent=e.agent, content=e.content, event_type=e.event_type, created_at=e.created_at)
        for e in result.scalars().all()
    ]


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events. If the run is still executing, streams new
    events live. If it already finished (or this process restarted and
    lost the in-memory queue), replays the persisted history once and
    closes -- either way the client gets the full event log.
    """
    run = await _get_owned_run(run_id, current_user, db)
    queue = run_manager.get_queue(str(run_id))

    async def event_stream():
        if queue is None:
            result = await db.execute(
                select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.created_at)
            )
            for e in result.scalars().all():
                yield f"data: {json.dumps({'type': 'log', 'agent': e.agent, 'text': e.content})}\n\n"
            yield f"data: {json.dumps({'type': 'done' if run.status == 'done' else 'error', 'run_id': str(run_id)})}\n\n"
            yield "event: end\ndata: {}\n\n"
            return

        while True:
            item = await queue.get()
            if item is None:
                yield "event: end\ndata: {}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{run_id}/download")
async def download_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await _get_owned_run(run_id, current_user, db)
    if not run.zip_path:
        raise HTTPException(404, "This run has no downloadable files (research-only runs produce none).")
    return FileResponse(
        run.zip_path,
        media_type="application/zip",
        filename=f"researchos-{run_id}.zip",
    )
