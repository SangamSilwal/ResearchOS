from langgraph.graph import StateGraph, END
from agents.state import ResearchState
from agents.orchestrator import OrchestratorAgent
from agents.researcher import ResearcherAgent
from agents.coder_agent import CoderAgent
from agents.critic_agent import CriticAgent
from agents.architect_agent import architect_node
from agents.planner_agent import PlannerAgent
from agents.summarizer_agent import SummarizerAgent


# NOTE: agents are constructed fresh inside each node function (instead of
# once as module-level singletons) so that model/API-key changes made
# through the web UI's settings page take effect on the very next run
# without needing to restart the process. This mirrors the pattern
# `architect_node` already used.

async def orchestrator_node(state: ResearchState) -> dict:
    return await OrchestratorAgent().run(state)


async def researcher_node(state: ResearchState) -> dict:
    agent = ResearcherAgent()
    await agent.initialize()
    return await agent.run(state)


async def coder_node(state: ResearchState) -> dict:
    return await CoderAgent().run(state)


async def critic_node(state: ResearchState) -> dict:
    return await CriticAgent().run(state)


async def planner_node(state: ResearchState) -> dict:
    return await PlannerAgent().run(state)


async def summarizer_node(state: ResearchState) -> dict:
    return await SummarizerAgent().run(state)


def route_from_orchestrator(state: ResearchState) -> str:
    next_agent = state.get("next_agent", "researcher")
    if next_agent in ("researcher", "architect", "coder", "critic", "planner"):
        return next_agent
    return "researcher"

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
    graph.add_node("planner", planner_node)
    graph.add_node("summarizer", summarizer_node)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "researcher": "researcher",
            "architect": "architect",
            "coder": "coder",
            "critic": "critic",
            "planner": "planner",
        },
    )

    graph.add_conditional_edges(
        "researcher",
        route_from_researcher,
        {"researcher": "researcher", "architect": "architect", "planner": "planner", "done": "summarizer"},
    )

    graph.add_edge("architect", "coder")

    graph.add_conditional_edges(
        "coder",
        route_from_coder,
        {"coder": "coder", "critic": "critic", "done": "summarizer"},
    )

    graph.add_conditional_edges(
        "critic",
        route_from_critic,
        {"critic": "critic", "coder": "coder", "done": "summarizer"},
    )

    graph.add_edge("planner","summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile()


# Kept for backwards compatibility (tests/full_graph_test.py imports this
# directly). Safe at import time: compiling the graph only wires up the
# node functions above, it does not construct any agent/LLM client until a
# node actually runs -- so it does not freeze API keys or model choices.
compiled_graph = build_graph()
