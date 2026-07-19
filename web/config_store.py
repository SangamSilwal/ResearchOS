"""
Persists web-UI-submitted configuration (provider API keys + per-agent
model choices + the web login account) into the project's .env file, and
keeps the in-memory `settings` singleton (and os.environ) in sync so the
change is picked up by the very next agent run -- no process restart
required.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import set_key

from core.config import settings

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"

# settings-attribute -> ENV var name
PROVIDER_KEY_FIELDS: dict[str, str] = {
    "tavily_api_key": "TAVILY_API_KEY",
    "github_token": "GITHUB_TOKEN",
    "groq_api_key": "GROQ_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
    "mistral_api_key": "MISTRAL_API_KEY",
    "openrouter_api_key": "OPENROUTER_API_KEY",
    "langchain_api_key": "LANGCHAIN_API_KEY",
}

AGENT_MODEL_FIELDS: dict[str, str] = {
    "orchestrator_model": "ORCHESTRATOR_MODEL",
    "researcher_model": "RESEARCHER_MODEL",
    "architect_model_a": "ARCHITECT_MODEL_A",
    "architect_model_b": "ARCHITECT_MODEL_B",
    "architect_judge_model": "ARCHITECT_JUDGE_MODEL",
    "coder_model": "CODER_MODEL",
    "critic_model": "CRITIC_MODEL",
    "planner_model": "PLANNER_MODEL",
    "summarizer_model": "SUMMARIZER_MODEL",
}

# Friendly label + which settings field holds the API key each provider
# prefix needs. Used both to render the settings form and to validate it.
PROVIDERS = {
    "groq": {"label": "Groq", "key_field": "groq_api_key"},
    "gemini": {"label": "Google Gemini", "key_field": "google_api_key"},
    "mistral": {"label": "Mistral", "key_field": "mistral_api_key"},
    "openrouter": {"label": "OpenRouter", "key_field": "openrouter_api_key"},
}

# Suggested model strings per provider, shown as <datalist> options. The
# form also accepts any free-text "provider/model-name" string, so this
# list is a convenience, not a hard restriction.
MODEL_SUGGESTIONS = {
    "groq": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-8b-instant",
        "groq/moonshotai/kimi-k2-instruct",
    ],
    "gemini": [
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-1.5-pro",
    ],
    "mistral": [
        "mistral/mistral-large-latest",
        "mistral/mistral-small-latest",
        "mistral/codestral-latest",
    ],
    "openrouter": [
        "openrouter/deepseek/deepseek-chat",
        "openrouter/qwen/qwen-2.5-coder-32b-instruct",
        "openrouter/nvidia/llama-3.1-nemotron-70b-instruct",
    ],
}

AGENT_FIELD_LABELS = {
    "orchestrator_model": "Orchestrator",
    "researcher_model": "Researcher",
    "architect_model_a": "Architect - Proposal A",
    "architect_model_b": "Architect - Proposal B",
    "architect_judge_model": "Architect - Judge",
    "coder_model": "Coder",
    "critic_model": "Critic",
    "planner_model": "Planner",
    "summarizer_model": "Summarizer",
}


def _ensure_env_file() -> None:
    if not ENV_PATH.exists():
        ENV_PATH.touch()


def apply_values(values: dict[str, str]) -> None:
    """
    Write the given {settings_field: value} pairs to .env, and update the
    live `settings` object + os.environ so the change is active immediately.
    """
    _ensure_env_file()
    all_fields = {**PROVIDER_KEY_FIELDS, **AGENT_MODEL_FIELDS,
                  "web_username": "WEB_USERNAME",
                  "web_password_hash": "WEB_PASSWORD_HASH"}

    for field, value in values.items():
        if field not in all_fields:
            continue
        env_name = all_fields[field]
        set_key(str(ENV_PATH), env_name, value or "")
        setattr(settings, field, value or "")
        os.environ[env_name] = value or ""


def model_provider(model_key: str) -> str | None:
    if "/" not in model_key:
        return None
    return model_key.split("/", 1)[0]


def missing_provider_keys() -> list[str]:
    """
    Returns the friendly provider labels that are referenced by at least
    one currently-configured agent model but have no API key saved yet.
    """
    used_providers = set()
    for field in AGENT_MODEL_FIELDS:
        provider = model_provider(getattr(settings, field, ""))
        if provider:
            used_providers.add(provider)

    missing = []
    for provider in used_providers:
        meta = PROVIDERS.get(provider)
        if not meta:
            continue
        if not getattr(settings, meta["key_field"], ""):
            missing.append(meta["label"])
    return missing


def is_configured() -> bool:
    """
    True once the operator has saved at least Tavily (required for web
    search) and every referenced model provider has a key on file.
    """
    if not settings.tavily_api_key:
        return False
    if missing_provider_keys():
        return False
    return True


def current_form_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for field in {**PROVIDER_KEY_FIELDS, **AGENT_MODEL_FIELDS}:
        values[field] = getattr(settings, field, "")
    return values
