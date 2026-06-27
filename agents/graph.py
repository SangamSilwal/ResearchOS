from langgraph.graph import StateGraph, END
from agents.state import ResearchState
from agents.orchestrator import OrchestratorAgent
from agents.researcher import ResearcherAgent
from agents.coder_agent import CoderAgent
from agents.critic_agent import CriticAgent
from agents.architect_agent import architect_node


_orchestrator_agent = OrchestratorAgent()


async def orchestrator_node(state: ResearchState) -> dict:
    return await _orchestrator_agent.run(state)


_researcher_agent = ResearcherAgent()
_researcher_initialized = False


async def researcher_node(state: ResearchState) -> dict:
    global _researcher_initialized
    if not _researcher_initialized:
        await _researcher_agent.initialize()
        _researcher_initialized = True
    return await _researcher_agent.run(state)


_coder_agent = CoderAgent()


async def coder_node(state: ResearchState) -> dict:
    return await _coder_agent.run(state)


_critic_agent = CriticAgent()


async def critic_node(state: ResearchState) -> dict:
    return await _critic_agent.run(state)


NOT_IMPLEMENTED_AGENTS = {"planner"}


async def not_implemented_node(state: ResearchState) -> dict:
    agent_name = state.get("next_agent", "unknown")
    raise NotImplementedError(
        f"'{agent_name}' agent is not implemented yet. "
        f"The orchestrator routed here, but only researcher, architect, "
        f"coder, and critic currently exist."
    )


def route_from_orchestrator(state: ResearchState) -> str:
    next_agent = state.get("next_agent", "researcher")
    if next_agent in NOT_IMPLEMENTED_AGENTS:
        return "not_implemented"
    if next_agent in ("researcher", "architect", "coder", "critic"):
        return next_agent
    return "not_implemented"


def route_from_researcher(state: ResearchState) -> str:
    return state.get("next_agent", "architect")


def route_from_coder(state: ResearchState) -> str:
    return state.get("next_agent", "done")


def route_from_critic(state: ResearchState) -> str:
    return state.get("next_agent", "done")


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("architect", architect_node)
    graph.add_node("coder", coder_node)
    graph.add_node("critic", critic_node)
    graph.add_node("not_implemented", not_implemented_node)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "researcher": "researcher",
            "architect": "architect",
            "coder": "coder",
            "critic": "critic",
            "not_implemented": "not_implemented",
        },
    )

    graph.add_conditional_edges(
        "researcher",
        route_from_researcher,
        {"researcher": "researcher", "architect": "architect"},
    )

    graph.add_edge("architect", "coder")

    graph.add_conditional_edges(
        "coder",
        route_from_coder,
        {"coder": "coder", "critic": "critic", "done": END},
    )

    graph.add_conditional_edges(
        "critic",
        route_from_critic,
        {"critic": "critic", "coder": "coder", "done": END},
    )

    return graph.compile()


compiled_graph = build_graph()