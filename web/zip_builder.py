"""Package a generated project directory into a downloadable zip."""
from __future__ import annotations

import os
import zipfile
from pathlib import Path


def build_project_zip(project_dir: str, zip_path: str) -> str:
    """
    Zip everything under project_dir (preserving relative paths).
    Returns the absolute path to the created zip file.
    """
    root = Path(project_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Project directory does not exist: {root}")

    dest = Path(zip_path).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    skip_dirs = {".venv", "__pycache__", ".git", "node_modules"}
    skip_suffixes = {".pyc", ".pyo"}

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for filename in filenames:
                if any(filename.endswith(s) for s in skip_suffixes):
                    continue
                full = Path(dirpath) / filename
                arcname = full.relative_to(root).as_posix()
                zf.write(full, arcname)

    return str(dest)
