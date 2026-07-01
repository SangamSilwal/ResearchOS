import json
import os
import sqlite3
import time
from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs(appname="researchos", appauthor="researchos")
DEFAULT_SQLITE_PATH = Path(_dirs.user_data_dir) / "memory.sqlite"
DEFAULT_RECENT_RUNS = 3


def _get_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres"):
        return url
    return None



def _sqlite_conn() -> sqlite3.Connection:
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DEFAULT_SQLITE_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_memory (
            project_id   TEXT PRIMARY KEY,
            goal         TEXT NOT NULL,
            created_at   REAL NOT NULL,
            files_written TEXT NOT NULL,   -- JSON list of paths
            flagged_tasks TEXT NOT NULL,   -- JSON list of task titles
            task_summary  TEXT NOT NULL    -- JSON dict {status: count}
        )
        """
    )
    conn.commit()
    return conn


def _sqlite_save(project_id: str, goal: str, files: list[str],
                 flagged: list[str], task_summary: dict) -> None:
    conn = _sqlite_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO run_memory
            (project_id, goal, created_at, files_written, flagged_tasks, task_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (project_id, goal, time.time(),
         json.dumps(files), json.dumps(flagged), json.dumps(task_summary)),
    )
    conn.commit()
    conn.close()


def _sqlite_recent(n: int) -> list[dict]:
    conn = _sqlite_conn()
    rows = conn.execute(
        """
        SELECT project_id, goal, created_at, files_written, flagged_tasks, task_summary
        FROM run_memory
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()
    conn.close()
    return [
        {
            "project_id": r[0],
            "goal": r[1],
            "created_at": r[2],
            "files_written": json.loads(r[3]),
            "flagged_tasks": json.loads(r[4]),
            "task_summary": json.loads(r[5]),
        }
        for r in rows
    ]



async def _pg_save(database_url: str, project_id: str, goal: str,
                   files: list[str], flagged: list[str], task_summary: dict) -> None:
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_memory (
                project_id   TEXT PRIMARY KEY,
                goal         TEXT NOT NULL,
                created_at   DOUBLE PRECISION NOT NULL,
                files_written JSONB NOT NULL,
                flagged_tasks JSONB NOT NULL,
                task_summary  JSONB NOT NULL
            )
            """
        )
        await conn.execute(
            """
            INSERT INTO run_memory
                (project_id, goal, created_at, files_written, flagged_tasks, task_summary)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (project_id) DO UPDATE SET
                goal          = EXCLUDED.goal,
                created_at    = EXCLUDED.created_at,
                files_written = EXCLUDED.files_written,
                flagged_tasks = EXCLUDED.flagged_tasks,
                task_summary  = EXCLUDED.task_summary
            """,
            project_id, goal, time.time(),
            json.dumps(files), json.dumps(flagged), json.dumps(task_summary),
        )
    finally:
        await conn.close()


async def _pg_recent(database_url: str, n: int) -> list[dict]:
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch(
            """
            SELECT project_id, goal, created_at, files_written,
                   flagged_tasks, task_summary
            FROM run_memory
            ORDER BY created_at DESC
            LIMIT $1
            """,
            n,
        )
    finally:
        await conn.close()
    return [
        {
            "project_id": r["project_id"],
            "goal": r["goal"],
            "created_at": r["created_at"],
            "files_written": json.loads(r["files_written"]),
            "flagged_tasks": json.loads(r["flagged_tasks"]),
            "task_summary": json.loads(r["task_summary"]),
        }
        for r in rows
    ]



async def save_run_memory(project_id: str, goal: str,
                          files: list[str], flagged: list[str],
                          task_summary: dict) -> None:
    """
    Call this at the end of a run to persist its summary.
    Works synchronously for SQLite (no async needed), async for
    Postgres -- callers just await it regardless.
    """
    database_url = _get_database_url()
    if database_url:
        await _pg_save(database_url, project_id, goal, files, flagged, task_summary)
    else:
        _sqlite_save(project_id, goal, files, flagged, task_summary)


async def get_recent_runs(n: int = DEFAULT_RECENT_RUNS) -> list[dict]:
    """
    Returns the n most recent run summaries, newest first.
    Used by agents to build cross-run context into their prompts.
    """
    database_url = _get_database_url()
    if database_url:
        return await _pg_recent(database_url, n)
    return _sqlite_recent(n)


def format_run_memory_for_prompt(runs: list[dict]) -> str:
    """
    Formats recent run summaries into a concise, agent-readable block
    for inclusion in a system or user prompt.
    """
    if not runs:
        return "(no previous runs recorded)"

    lines = []
    for r in runs:
        status_str = ", ".join(f"{k}: {v}" for k, v in r["task_summary"].items())
        flagged_str = (
            f"  flagged for human review: {', '.join(r['flagged_tasks'])}"
            if r["flagged_tasks"] else ""
        )
        files_str = (
            f"  files written: {', '.join(r['files_written'][:5])}"
            + (" ..." if len(r["files_written"]) > 5 else "")
            if r["files_written"] else ""
        )
        lines.append(
            f"- Goal: {r['goal']}\n"
            f"  Tasks: {status_str}\n"
            f"{files_str}\n"
            f"{flagged_str}"
        )
    return "\n".join(lines).strip()