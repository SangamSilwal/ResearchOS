"""
/api/runs — start agent runs, poll status, stream events, download zip.
"""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user
from models import Message, Run, RunEvent, Thread, User
from model_resolver import MissingApiKeyError, resolve_all_roles
from run_type import infer_run_type
from schemas import RunCreate, RunDetailOut, RunEventOut, RunOut

router = APIRouter(prefix="/api/runs", tags=["runs"])


async def _get_owned_thread(db: AsyncSession, thread_id: uuid.UUID, user: User) -> Thread:
    result = await db.execute(
        select(Thread).where(Thread.id == thread_id, Thread.user_id == user.id)
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found.")
    return thread


async def _get_owned_run(db: AsyncSession, run_id: uuid.UUID, user: User) -> Run:
    result = await db.execute(
        select(Run).join(Thread, Run.thread_id == Thread.id)
        .where(Run.id == run_id, Thread.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run


@router.post("", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: RunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    thread = await _get_owned_thread(db, payload.thread_id, user)

    try:
        await resolve_all_roles(db, user.id)
    except MissingApiKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    run_type = payload.type
    if run_type not in ("build", "research"):
        run_type = infer_run_type(payload.goal)

    user_message = Message(thread_id=thread.id, role="user", content=payload.goal)
    db.add(user_message)
    await db.flush()

    run = Run(
        thread_id=thread.id,
        message_id=user_message.id,
        goal=payload.goal,
        type=run_type,
        status="queued",
    )
    db.add(run)

    if payload.goal and thread.title == "New conversation":
        thread.title = payload.goal[:80].strip() or thread.title

    await db.commit()
    await db.refresh(run)

    from worker.tasks import run_agent_pipeline

    run_agent_pipeline.delay(str(run.id))

    return run


@router.get("", response_model=list[RunOut])
async def list_runs(
    thread_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(Run)
        .join(Thread, Run.thread_id == Thread.id)
        .where(Thread.user_id == user.id)
        .order_by(Run.created_at.desc())
    )
    if thread_id is not None:
        await _get_owned_thread(db, thread_id, user)
        query = query.where(Run.thread_id == thread_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{run_id}", response_model=RunDetailOut)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Run)
        .options(selectinload(Run.events))
        .join(Thread, Run.thread_id == Thread.id)
        .where(Run.id == run_id, Thread.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run


@router.get("/{run_id}/events", response_model=list[RunEventOut])
async def list_run_events(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_run(db, run_id, user)
    result = await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.created_at.asc())
    )
    return result.scalars().all()


@router.get("/{run_id}/download")
async def download_run_zip(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = await _get_owned_run(db, run_id, user)

    if run.type != "build":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Research-goal runs don't produce a zip — check the thread's messages instead.",
        )
    if run.status != "done":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is not finished yet (status: {run.status}).",
        )
    if not run.zip_path or not os.path.isfile(run.zip_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No zip file on record for this run.",
        )

    filename = f"{run.goal[:50].strip().replace(' ', '_') or 'researchos_build'}.zip"
    return FileResponse(
        path=run.zip_path,
        filename=filename,
        media_type="application/zip",
    )
