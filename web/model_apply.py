"""
Apply per-user resolved model configs to settings and live agent instances.

Called once at the start of each Celery pipeline run. Celery workers handle
one task at a time per process, so mutating module-level singletons is safe.
"""
from __future__ import annotations

from core.config import settings
from llm.router import get_llm
from model_resolver import ResolvedModel, system_anthropic_key
from models import AgentRole, LLMProvider


ROLE_SETTINGS_ATTR: dict[AgentRole, str] = {
    AgentRole.orchestrator: "orchestrator_model",
    AgentRole.researcher: "researcher_model",
    AgentRole.architect_a: "architect_model_a",
    AgentRole.architect_b: "architect_model_b",
    AgentRole.planner: "planner_model",
    AgentRole.coder: "coder_model",
    AgentRole.critic: "critic_model",
    AgentRole.judge: "architect_judge_model",
    AgentRole.summarizer: "summarizer_model",
}


def _model_key(resolved: ResolvedModel) -> str:
    return f"{resolved.provider.value}/{resolved.model_name}"


def _api_key_for(resolved: ResolvedModel) -> str | None:
    if resolved.provider == LLMProvider.anthropic:
        return system_anthropic_key()
    return resolved.api_key


def apply_resolved_models(resolved: dict[AgentRole, ResolvedModel]) -> None:
    """Patch settings + singleton agent LLMs for this run."""
    for role, model in resolved.items():
        attr = ROLE_SETTINGS_ATTR[role]
        setattr(settings, attr, _model_key(model))

    from agents import graph as graph_module

    graph_module._orchestrator_agent.llm = get_llm(
        _model_key(resolved[AgentRole.orchestrator]),
        api_key=_api_key_for(resolved[AgentRole.orchestrator]),
    )
    graph_module._researcher_agent.llm = get_llm(
        _model_key(resolved[AgentRole.researcher]),
        api_key=_api_key_for(resolved[AgentRole.researcher]),
    )
    graph_module._coder_agent.llm = get_llm(
        _model_key(resolved[AgentRole.coder]),
        api_key=_api_key_for(resolved[AgentRole.coder]),
    )
    graph_module._critic_agent.llm = get_llm(
        _model_key(resolved[AgentRole.critic]),
        api_key=_api_key_for(resolved[AgentRole.critic]),
    )
    graph_module._planner_agent.llm = get_llm(
        _model_key(resolved[AgentRole.planner]),
        api_key=_api_key_for(resolved[AgentRole.planner]),
    )
    graph_module._summarizer_agent.llm = get_llm(
        _model_key(resolved[AgentRole.summarizer]),
        api_key=_api_key_for(resolved[AgentRole.summarizer]),
    )
