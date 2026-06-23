import pytest
from agents.state import ResearchState


 
@pytest.mark.asyncio
async def test_orchestrator_only():
    from agents.orchestrator import OrchestratorAgent
 
    agent = OrchestratorAgent()
    state: ResearchState = {
        "goal": "Build a REST API with FastAPI and PostgreSQL",
        "messages": [],
        "tasks": [],
        "research_findings": [],
        "output": {},
        "next_agent": "orchestrator",
        "error": None,
        "project_id": None,
    }
 
    result = await agent(state)
 
    print("\n── Orchestrator output ──")
    print(f"  Tasks: {len(result.get('tasks', []))}")
    print(f"  Next agent: {result.get('next_agent')}")
    for task in result.get("tasks", []):
        print(f"    - {task['title']} → {task['agent']}")
 
    assert len(result.get("tasks", [])) > 0
    assert result.get("next_agent") is not None
 
