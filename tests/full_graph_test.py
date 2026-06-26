import os
import shutil
import pytest
 
from agents.state import ResearchState
from core.config import settings

GOAL = "Build a REST API with FastAPI and PostgreSQL"
 
 
def make_initial_state(**overrides) -> ResearchState:
    state: ResearchState = {
        "goal": GOAL,
        "messages": [],
        "tasks": [],
        "research_findings": [],
        "output": {},
        "next_agent": "orchestrator",
        "error": None,
        "project_id": "pytest_run",
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_full_graph(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", str(tmp_path))
 
    from agents.graph import compiled_graph
 
    state = make_initial_state()
 
    result = await compiled_graph.ainvoke(state)
 
    print("\n── Full graph output ──")
    print(f"  Total tasks: {len(result.get('tasks', []))}")
    by_agent = {}
    for t in result.get("tasks", []):
        by_agent.setdefault(t["agent"], []).append(t["status"])
    for agent_name, statuses in by_agent.items():
        print(f"    {agent_name}: {statuses}")
 
    design = result.get("architecture_design", {})
    print(f"  Architecture components: {len(design.get('components', []))}")
 
    written_files = []
    for t in result.get("tasks", []):
        if t.get("agent") == "coder" and t.get("output_path"):
            written_files.append(t["output_path"])
    print(f"  Files written: {written_files}")
 
    assert result.get("research_findings")
    assert design.get("components") is not None
    assert any(t["agent"] == "coder" for t in result["tasks"])
    for t in result["tasks"]:
        if t.get("agent") == "coder" and t.get("status") == "done":
            assert os.path.exists(t["output_path"])
