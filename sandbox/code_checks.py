"""
code_checks.py

Lightweight, sandboxed checks run against a generated file before the
LLM-based quality review even happens. These catch hard failures
(syntax errors, import errors) cheaply and deterministically, so the
LLM reviewer isn't wasted on code that doesn't even parse.

Both checks accept a `python_executable` argument -- pass the
project's own venv interpreter (see agents/project_venv.py) rather
than sys.executable, so the import check runs against an environment
that actually has the generated project's real dependencies
installed. Defaults to sys.executable only as a fallback for
non-Python-project use (e.g. ad-hoc testing).

Safety notes:
- Only .py files are executed/imported; other file types get a
  syntax-only or no-op check (extend FILE_CHECKERS as needed).
- Both checks run in a SEPARATE SUBPROCESS with a timeout, never
  in-process -- a subprocess crash, hang, or resource issue can't
  take down the main agent process.
- Import-checking actually executes module-level code, which is
  inherently less safe than a pure syntax check (the generated code
  could perform file/network I/O at import time). This is a known,
  accepted risk tradeoff for "really check it works" rather than
  "just check it parses" -- if you need stronger isolation later,
  run this in a container or restricted user rather than a bare
  subprocess.
"""

import subprocess
import sys
import os


EXECUTION_TIMEOUT_SECONDS = 10


def _run_subprocess(cmd: list[str], cwd: str | None = None) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT_SECONDS,
        )
        ok = result.returncode == 0
        output = (result.stdout or "") + (result.stderr or "")
        return ok, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Execution timed out after {EXECUTION_TIMEOUT_SECONDS}s"
    except OSError as e:
        return False, f"{type(e).__name__}: {e}"


def check_python_syntax(file_path: str, python_executable: str | None = None) -> tuple[bool, str]:
    """py_compile in a subprocess -- pure syntax check, no execution
    of module-level code, so this is always safe to run. The venv's
    interpreter vs sys.executable doesn't matter for syntax checking
    (same Python grammar), but accepting it keeps the call sites
    uniform with check_python_import."""
    python = python_executable or sys.executable
    return _run_subprocess([python, "-m", "py_compile", file_path])


def check_python_import(file_path: str, python_executable: str | None = None) -> tuple[bool, str]:
    """
    Attempts to import the file as a module in an isolated subprocess
    with its own cwd set to the file's directory (so sibling-relative
    imports inside the generated project have a chance of resolving).
    This DOES execute module-level code -- see module docstring.

    Uses python_executable (the project's venv interpreter) so
    third-party imports like `fastapi` or `sqlalchemy` resolve against
    packages actually installed for this project, not whatever
    happens to be installed for the researchos tool itself.
    """
    python = python_executable or sys.executable
    module_dir = os.path.dirname(file_path) or "."
    module_name = os.path.splitext(os.path.basename(file_path))[0]

    snippet = (
        f"import sys; sys.path.insert(0, {module_dir!r}); "
        f"import {module_name}"
    )
    return _run_subprocess([python, "-c", snippet], cwd=module_dir)


def check_generic_non_empty(file_path: str) -> tuple[bool, str]:
    """Fallback for non-Python files: just confirm something was written."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            return False, "File is empty."
        return True, ""
    except OSError as e:
        return False, f"{type(e).__name__}: {e}"


def run_execution_checks(file_path: str, python_executable: str | None = None) -> dict:
    """
    Returns:
        {
          "passed": bool,
          "checks": [{"name": str, "passed": bool, "output": str}, ...]
        }
    Stops at the first failing check (no point import-checking code
    that doesn't even parse) but always returns the full list of
    checks attempted, for transparency in logs/critic feedback.

    python_executable should be the project's own venv interpreter
    (see agents/project_venv.py:ensure_venv) so dependency imports
    resolve correctly; falls back to sys.executable if not provided.
    """
    checks_run = []

    if file_path.endswith(".py"):
        ok, output = check_python_syntax(file_path, python_executable)
        checks_run.append({"name": "syntax_check", "passed": ok, "output": output})
        if not ok:
            return {"passed": False, "checks": checks_run}

        ok, output = check_python_import(file_path, python_executable)
        checks_run.append({"name": "import_check", "passed": ok, "output": output})
        if not ok:
            return {"passed": False, "checks": checks_run}

        return {"passed": True, "checks": checks_run}

    ok, output = check_generic_non_empty(file_path)
    checks_run.append({"name": "non_empty_check", "passed": ok, "output": output})
    return {"passed": ok, "checks": checks_run}