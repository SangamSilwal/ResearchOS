"""/api/threads — conversation CRUD, scoped to the current user."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user
from models import Thread, User
from schemas import ThreadCreate, ThreadDetailOut, ThreadOut

router = APIRouter(prefix="/api/threads", tags=["threads"])


async def _get_owned_thread(db: AsyncSession, thread_id: uuid.UUID, user: User) -> Thread:
    result = await db.execute(
        select(Thread)
        .options(selectinload(Thread.messages))
        .where(Thread.id == thread_id, Thread.user_id == user.id)
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found.")
    return thread


@router.get("", response_model=list[ThreadOut])
async def list_threads(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Thread).where(Thread.user_id == user.id).order_by(Thread.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
async def create_thread(
    payload: ThreadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    thread = Thread(user_id=user.id, title=payload.title or "New conversation")
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


@router.get("/{thread_id}", response_model=ThreadDetailOut)
async def get_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_owned_thread(db, thread_id, user)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    thread = await _get_owned_thread(db, thread_id, user)
    await db.delete(thread)
    await db.commit()