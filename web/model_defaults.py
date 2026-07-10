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