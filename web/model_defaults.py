<<<<<<< ours
from .models import AgentRole, LLMProvider


DEFAULT_AGENT_MODELS: dict[AgentRole, tuple[LLMProvider, str]] = {
    AgentRole.orchestrator: (LLMProvider.anthropic, "claude-sonnet-5"),
    AgentRole.researcher:   (LLMProvider.anthropic, "claude-sonnet-5"),
    AgentRole.architect:    (LLMProvider.anthropic, "claude-opus-4-8"),
    AgentRole.planner:      (LLMProvider.anthropic, "claude-sonnet-5"),
    AgentRole.coder:        (LLMProvider.anthropic, "claude-sonnet-5"),
    AgentRole.critic:       (LLMProvider.anthropic, "claude-haiku-4-5-20251001"),
    AgentRole.judge:        (LLMProvider.anthropic, "claude-opus-4-8"),
}
=======
"""
Default model per agent role -- what a brand new, unconfigured account
runs on. All default to Groq (the platform-default provider, billed to
the app's own key) so a user can submit a goal immediately after
logging in, with zero setup. They can override any of these from
/api/settings/agent-models once they've optionally added their own
BYO provider keys.

Kept in sync with core.config.Settings' own per-field defaults --
those are what run.py (the CLI) uses, these are what a fresh web
account uses. They intentionally match.
"""
from __future__ import annotations

from web.models import AgentRole

# role -> "provider/model-name"
DEFAULT_AGENT_MODELS: dict[AgentRole, str] = {
    AgentRole.orchestrator: "groq/llama-3.3-70b-versatile",
    AgentRole.researcher: "groq/llama-3.3-70b-versatile",
    AgentRole.architect_a: "groq/llama-3.3-70b-versatile",
    AgentRole.architect_b: "groq/llama-3.3-70b-versatile",
    AgentRole.judge: "groq/llama-3.3-70b-versatile",
    AgentRole.planner: "groq/llama-3.3-70b-versatile",
    AgentRole.coder: "groq/llama-3.3-70b-versatile",
    AgentRole.critic: "groq/llama-3.1-8b-instant",
    AgentRole.summarizer: "groq/llama-3.1-8b-instant",
}

# AgentRole -> the core.config.Settings field name each one maps to when
# building a run's model overrides (see web/config_resolution.py).
AGENT_ROLE_SETTINGS_FIELD: dict[AgentRole, str] = {
    AgentRole.orchestrator: "orchestrator_model",
    AgentRole.researcher: "researcher_model",
    AgentRole.architect_a: "architect_model_a",
    AgentRole.architect_b: "architect_model_b",
    AgentRole.judge: "architect_judge_model",
    AgentRole.planner: "planner_model",
    AgentRole.coder: "coder_model",
    AgentRole.critic: "critic_model",
    AgentRole.summarizer: "summarizer_model",
}
>>>>>>> theirs
