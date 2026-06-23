import pytest
from agents.state import ResearchState

@pytest.mark.asyncio
async def test_researcher_only():
    from agents.researcher import ResearcherAgent
    agent = ResearcherAgent()
    await agent.initialize()
    state: ResearchState = {
        "goal": "Build a REST API with FastAPI and PostgreSQL",
        "messages": [],
        "tasks": [
            {
                "id": 1,
                "title": "Research FastAPI",
                "description": "Research FastAPI best practices",
                "agent": "researcher",
                "status": "pending",
            }
        ],
        "research_findings": [],
        "output": {},
        "next_agent": "researcher",
        "error": None,
        "project_id": None,
    }
    result = await agent.run(state)
    print("\n── Researcher output ──\n")
    print(f"  Findings: {len(result.get('research_findings', []))}")
    print(f"  Next agent: {result.get('next_agent')}")
    if result.get("research_findings"):
        finding = result["research_findings"][0]
        print(f"  Task: {finding['task_title']}")
        print(f"  Sources: {len(finding.get('sources', []))}")
    assert len(result.get("research_findings", [])) > 0
    assert result.get("next_agent") is not None

