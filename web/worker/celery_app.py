"""
Celery application for ResearchOS background agent runs.

Start from the web/ directory:
    celery -A worker.celery_app worker --loglevel=info
"""
from __future__ import annotations

import bootstrap  # noqa: F401

import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("researchos", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

import worker.tasks  # noqa: E402, F401 — register tasks with the app
