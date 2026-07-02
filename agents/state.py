from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

 
class ResearchState(TypedDict):
    goal: str
    messages: Annotated[list, add_messages]
    tasks: list[dict[str, Any]]
    research_findings: list[dict[str, Any]]
    architecture_design: dict[str, Any]
    architecture_competition: dict[str, Any]
    output: dict[str, Any]
    summary: str | None
    next_agent: str
    error: str | None
    project_id: str | None
