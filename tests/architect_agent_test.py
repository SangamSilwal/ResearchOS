import pytest
from agents.state import ResearchState
import pprint

@pytest.mark.asyncio
async def test_architect_only():
    from agents.architect_agent import architech_node
    state:ResearchState = {
    "goal":"Fast API best practices",
  "messages": [
    {
      "type": "AIMessage",
      "content": "[Researcher] Completed: Research FastAPI"
    }
  ],
  "tasks": [
    {
      "id": 1,
      "title": "Research FastAPI",
      "description": "Research FastAPI best practices",
      "agent": "researcher",
      "status": "done"
    }
  ],
  "research_findings": [
    {
      "task_id": 1,
      "task_title": "Research FastAPI",
      "summary": {
        "title": "FastAPI Best Practices Research Summary",
        "sections": {
          "Introduction": [
            "FastAPI is a modern, high-performance Python web framework.",
            "Uses Python type hints and Pydantic for validation.",
            "Automatically generates OpenAPI documentation."
          ],
          "Project Setup and Structure": [
            "Create a project directory and virtual environment.",
            "Install required packages.",
            "Organize code into routes, models, and database modules."
          ],
          "REST API Design": [
            "Use correct HTTP verbs (GET, POST, PUT, DELETE).",
            "Follow standard REST conventions.",
            "Use meaningful endpoint names.",
            "Generate API docs using OpenAPI."
          ],
          "Database Interactions": [
            "Use SQLAlchemy or another ORM.",
            "Keep database logic in dedicated modules."
          ],
          "Business Logic and Services": [
            "Separate business logic from API routes.",
            "Use a service layer.",
            "Apply the repository pattern for data access."
          ],
          "Conclusion": [
            "No relevant arXiv papers were found.",
            "Recommendations are based on web articles and GitHub repositories."
          ]
        },
        "recommendations": [
          "Follow REST API standards.",
          "Use SQLAlchemy for persistence.",
          "Separate concerns with service layers.",
          "Use repository patterns.",
          "Leverage OpenAPI documentation."
        ],
        "tools_and_frameworks": [
          "FastAPI",
          "SQLAlchemy",
          "Pydantic",
          "OpenAPI"
        ]
      },
      "sources": [
        "https://www.sqlservercentral.com/articles/building-a-restful-api-with-fastapi-and-postgresql",
        "https://github.com/jod35/Build-a-fastapi-and-postgreSQL-API-with-SQLAlchemy",
        "https://www.geeksforgeeks.org/python/fastapi-rest-architecture",
        "https://auth0.com/blog/fastapi-best-practices",
        "https://medium.com/@lautisuarez081/fastapi-best-practices-and-design-patterns-building-quality-python-apis-31774ff3c28a",
        "http://arxiv.org/abs/1411.4413v2"
      ]
    }
  ],
  "next_agent": "architect"
}
    result = await architech_node(state)
    pprint.pprint(result)

