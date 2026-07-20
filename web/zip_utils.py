from __future__ import annotations

import os
import zipfile
from pathlib import Path

from core.config import settings


def zip_run_output(run_id: str) -> str | None:
    """
    Zips <output_dir>/<run_id>/ (where the coder agent writes files --
    see agents/coder_agent.py's _resolve_output_path) into
    <downloads_dir>/<run_id>.zip. Returns the zip path, or None if the
    run produced no files (e.g. a research-only run).
    """
    source_dir = Path(settings.output_dir).resolve() / run_id
    if not source_dir.is_dir() or not any(source_dir.rglob("*")):
        return None

    downloads_dir = Path(settings.downloads_dir).resolve()
    downloads_dir.mkdir(parents=True, exist_ok=True)
    zip_path = downloads_dir / f"{run_id}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=str(file_path.relative_to(source_dir)))

    return str(zip_path)
