"""Celery tasks for executing ResearchOS agent pipelines."""
from __future__ import annotations

import asyncio
import uuid

from worker.celery_app import celery_app


@celery_app.task(bind=True, name="run_agent_pipeline")
def run_agent_pipeline(self, run_id: str) -> None:
    from pipeline import execute_run

    asyncio.run(execute_run(uuid.UUID(run_id), celery_task_id=self.request.id))
