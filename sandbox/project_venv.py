"""
sandbox/project_venv.py

Each generated project gets its own isolated virtual environment,
scoped by project_id, so:
  - the critic's import checks run against an environment that
    actually has the project's real dependencies installed
  - different researchos runs with conflicting dependency needs
    never collide
  - the researchos tool's own environment is never polluted with
    whatever a generated architecture happens to need

The venv is created once per project (lazily, on first use) and
reused for every coder/critic call within that run.
"""

import os
import re
import subprocess
import sys
import venv
from pathlib import Path

from core.config import settings

INSTALL_TIMEOUT_SECONDS = 120

# Common cases where the PyPI install name differs from the import
# name. Not exhaustive -- extend as you hit more of these in
# practice. This is only used as a fallback guess if the architect's
# dependencies list doesn't already specify the correct PyPI name.
IMPORT_TO_PYPI = {
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "cv2": "opencv-python",
    "dotenv": "python-dotenv",
    "bs4": "beautifulsoup4",
    "jwt": "PyJWT",
    "sklearn": "scikit-learn",
}


def _venv_dir(project_id: str) -> Path:
    base = Path(settings.output_dir).resolve() / project_id / ".venv"
    return base


def _venv_python(project_id: str) -> Path:
    venv_path = _venv_dir(project_id)
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def ensure_venv(project_id: str) -> Path:
    """
    Creates the project's venv if it doesn't already exist. Returns
    the path to that venv's python executable, for use by code_checks
    instead of sys.executable.
    """
    venv_path = _venv_dir(project_id)
    python_path = _venv_python(project_id)

    if python_path.exists():
        return python_path

    venv_path.parent.mkdir(parents=True, exist_ok=True)
    venv.EnvBuilder(with_pip=True, clear=False).create(str(venv_path))
    return python_path


def install_packages(project_id: str, packages: list[str]) -> tuple[bool, str]:
    """
    Installs the given list of PyPI package names into the project's
    venv. Safe to call with an empty list (no-op). Returns
    (success, combined_output) -- failures are surfaced, not raised,
    so a single bad/typo'd dependency doesn't crash the whole run;
    the critic will see the resulting import failure and can report
    it as feedback instead.
    """
    packages = [p for p in packages if p and p.strip()]
    if not packages:
        return True, ""

    python_path = ensure_venv(project_id)

    try:
        result = subprocess.run(
            [str(python_path), "-m", "pip", "install", "--quiet", *packages],
            capture_output=True,
            text=True,
            timeout=INSTALL_TIMEOUT_SECONDS,
        )
        ok = result.returncode == 0
        output = (result.stdout or "") + (result.stderr or "")
        return ok, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"pip install timed out after {INSTALL_TIMEOUT_SECONDS}s for: {packages}"
    except OSError as e:
        return False, f"{type(e).__name__}: {e}"


_IMPORT_LINE_RE = re.compile(
    r"^\s*(?:from\s+([a-zA-Z0-9_]+)|import\s+([a-zA-Z0-9_]+))", re.MULTILINE
)

# A reasonably thorough standard-library list for filtering -- not
# exhaustive across every Python version, but covers the common ones
# likely to appear in generated code. Anything not in here AND not
# already installed will be treated as a third-party package to
# install.
_STDLIB_MODULES = {
    "os", "sys", "re", "json", "time", "datetime", "math", "random",
    "collections", "itertools", "functools", "typing", "asyncio",
    "subprocess", "pathlib", "logging", "argparse", "uuid", "io",
    "shutil", "tempfile", "unittest", "abc", "enum", "dataclasses",
    "contextlib", "copy", "csv", "sqlite3", "socket", "threading",
    "multiprocessing", "queue", "string", "textwrap", "traceback",
    "warnings", "weakref", "hashlib", "hmac", "base64", "struct",
    "pickle", "http", "urllib", "email", "html", "xml", "decimal",
    "fractions", "statistics", "secrets", "platform", "getpass",
}


def detect_missing_imports(file_content: str, declared_dependencies: list[str]) -> list[str]:
    """
    Scans a generated file's top-level import statements and returns
    likely-missing PyPI package names: anything imported that isn't
    a standard-library module and isn't already covered by the
    architect's declared dependencies. This is a static-analysis
    fallback for when the architect's dependency list was incomplete
    -- it errs toward over-detecting (a redundant install attempt is
    harmless) rather than under-detecting (which would surface as a
    confusing import error later).
    """
    declared_lower = {d.lower() for d in declared_dependencies}

    found_modules = set()
    for match in _IMPORT_LINE_RE.finditer(file_content):
        module = match.group(1) or match.group(2)
        if not module:
            continue
        top_level = module.split(".")[0]
        found_modules.add(top_level)

    missing = []
    for module in found_modules:
        if module in _STDLIB_MODULES:
            continue
        pypi_name = IMPORT_TO_PYPI.get(module, module)
        if pypi_name.lower() in declared_lower or module.lower() in declared_lower:
            continue
        missing.append(pypi_name)

    return missing