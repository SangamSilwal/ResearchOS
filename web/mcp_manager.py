"""
ResearchOS normally expects the two local MCP servers (web search, arxiv)
to be started separately -- either by docker-compose or by hand in two
terminals (see README). For a single "deploy this and it just works" web
process, we spawn them ourselves as subprocesses instead, and restart the
web-search one whenever the Tavily key changes via the settings page.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class MCPManager:
    def __init__(self) -> None:
        self._procs: dict[str, subprocess.Popen] = {}

    def _spawn(self, name: str, module: str, port: int, extra_env: dict[str, str]) -> None:
        self.stop(name)
        env = os.environ.copy()
        env["MCP_HOST"] = "0.0.0.0"
        env["MCP_PORT"] = str(port)
        env.update(extra_env)
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", module],
                cwd=str(REPO_ROOT),
                env=env,
            )
            self._procs[name] = proc
        except OSError:
            # Non-fatal: the researcher agent will simply fail to reach
            # this tool and surface that error inside the run itself.
            pass

    def start_all(self) -> None:
        from core.config import settings
        self._spawn(
            "web_search", "mcp_servers.web_search.server", 8000,
            {"TAVILY_API_KEY": settings.tavily_api_key},
        )
        self._spawn("arxiv", "mcp_servers.arxiv_mcp.server_arxiv", 8001, {})

    def restart_web_search(self) -> None:
        from core.config import settings
        self._spawn(
            "web_search", "mcp_servers.web_search.server", 8000,
            {"TAVILY_API_KEY": settings.tavily_api_key},
        )

    def stop(self, name: str) -> None:
        proc = self._procs.pop(name, None)
        if proc and proc.poll() is None:
            proc.terminate()

    def stop_all(self) -> None:
        for name in list(self._procs):
            self.stop(name)

    def status(self) -> dict[str, bool]:
        return {name: proc.poll() is None for name, proc in self._procs.items()}


mcp_manager = MCPManager()
