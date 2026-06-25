from langgraph.graph import StateGraph, END
from agents.state import ResearchState
from agents.researcher import ResearcherAgent
from agents.architect_agent import architech_node

_researcher_agent = ResearcherAgent()
_researcher_initialized = False

async def researcher_node(state: ResearchState) -> dict:
    global _researcher_initialized
    if not _researcher_initialized:
        await _researcher_agent.initialize()
        _researcher_initialized = True
    return await _researcher_agent.run(state)


async def coder_node(state: ResearchState) -> dict:
    # Placeholder until CoderAgent exists -- consumes the "coder"
    # tagged tasks the architect step created.
    pending = [
        t for t in state.get("tasks", [])
        if t.get("agent") == "coder" and t.get("status") == "pending"
    ]
    if not pending:
        return {"next_agent": "done"}
    # TODO: replace with real CoderAgent.run(state)
    raise NotImplementedError("CoderAgent not implemented yet")
 
 
def route_from_researcher(state: ResearchState) -> str:
    return state.get("next_agent", "architect")
 
 
# def route_from_architect(state: ResearchState) -> str:
#     return state.get("next_agent", "coder")


def build_graph():

    graph = StateGraph(ResearchState)
    graph.add_node("researcher",researcher_node)
    graph.add_node("architect",architech_node)
    # graph.add_node("coder",coder_node)

    graph.set_entry_point("researcher")

    graph.add_conditional_edges(
        "researcher",
        route_from_researcher,
        {"researcher":"researcher","architect":"architect"}
    )

    # graph.add_conditional_edges(
    #     "architect",
    #     route_from_architect,
    #     {"coder":"coder","done":END}
    # )

    graph.add_edge("architect",END)
    return graph.compile()

compiled_graph = build_graph()