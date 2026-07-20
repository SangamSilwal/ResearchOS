"""
Per-run LLM configuration.

Before this existed, agents read `core.config.settings` directly, which
is a single process-wide object. That's fine for the CLI (one user, one
process) but wrong for a multi-user API: two users' runs can be
in-flight concurrently on the same event loop, and if resolving one
user's model/API key ever meant mutating a shared global, one user's
requests could pick up another user's key.

Instead, each run's resolved config is stored in a contextvars.ContextVar.
asyncio propagates context per-Task, so a run started with
`asyncio.create_task(...)` (see web/run_manager.py) keeps its own config
for its entire lifetime, isolated from any other concurrently-running
task -- no shared mutable state, no locking needed.

`run.py` (the CLI) never sets this, so `resolve_model()` always falls
through to the `fallback` argument -- i.e. exactly the pre-existing
`core.config.settings` values. Nothing about the CLI's behavior changes.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass, field

# Providers actually implemented in llm/router.py. Kept here too so
# resolve_model() can decide whether a per-user key is even relevant for
# a given model string.
SUPPORTED_PROVIDERS = ("groq", "gemini", "mistral", "openrouter")


@dataclass
class RunConfig:
    # e.g. {"orchestrator_model": "groq/llama-3.3-70b-versatile", ...}
    models: dict[str, str] = field(default_factory=dict)
    # e.g. {"gemini": "AIza...", "mistral": "...", "openrouter": "sk-or-..."}
    # Deliberately keyed by provider, not stored per-agent -- one BYO key
    # per provider covers every agent role that happens to use it.
    keys: dict[str, str] = field(default_factory=dict)


_current: contextvars.ContextVar[RunConfig | None] = contextvars.ContextVar(
    "researchos_run_config", default=None
)


def set_run_config(config: RunConfig | None):
    """Returns a token; pass it to reset_run_config() when the run ends."""
    return _current.set(config)


def reset_run_config(token) -> None:
    _current.reset(token)


def get_run_config() -> RunConfig | None:
    return _current.get()


def resolve_model(field_name: str, fallback: str) -> tuple[str, str | None]:
    """
    Returns (model_key, api_key).

    model_key: the current run's override for `field_name` (e.g.
    "orchestrator_model") if one was set, otherwise `fallback` (the
    value baked into core.config.settings).

    api_key: the current run's BYO key for that model's provider, if
    any. None means "no per-user override" -- llm.router.get_llm()
    falls back to the platform's own key from core.config.settings in
    that case.
    """
    cfg = _current.get()
    model_key = fallback
    if cfg and cfg.models.get(field_name):
        model_key = cfg.models[field_name]

    api_key = None
    if cfg and "/" in model_key:
        provider = model_key.split("/", 1)[0]
        api_key = cfg.keys.get(provider)
    return model_key, api_key
