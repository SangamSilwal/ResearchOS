from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings

class ResearcherAgent(BaseAgent):

    def __init__(self):
        super().__init__(settings.researcher_model)
        self.mcp_client = MultiServerMCPClient(
            {
                "web_search": {
                    "url":"http://localhost:8000/mcp",
                    "transport":"streamable_http",
                }
            }
        )

        self.web_search_tool = None

    async def initialize(self):
        tools = await self.mcp_client.get_tools()
        self.web_search_tool = next(
            tool 
            for tool in tools
            if tool.name == "web_search"
        )

    def system_prompt(self) -> str:
        return """
        You are the Researcher agent of ResearchOS.

        You receive search results and synthesize them into clear,
        structured findings.

        For each topic:
        - Extract the most important facts and insights
        - Note best practices and recommendations
        - Identify tools, frameworks, and concepts
        - Flag contradictory or outdated information

        Be concise but complete.
        Use clear sections and bullet points.
        """
    
    async def run(self, state: ResearchState) -> dict:
        research_tasks = [
            t
            for t in state.get("tasks",[])
            if t.get("agent") == "researcher" and t.get("status") == "pending"
        ]

        if not research_tasks:

            return {
                "messages":[
                    AIMessage(
                        content="[Researcher] No pending research tasks"
                    )
                ],
                "next_agent":"architect"
            }
        task = research_tasks[0]
        query = f"{state['goal']} - {task['description']}"

        search_results = await self.web_search_tool.ainvoke(
            {
                "query":query,
                "max_results":5
            }
        )
        results_text = "\n\n".join(
            [
                f"Source: {r.get('url', 'unknown')}\n"
                f"{r.get('content', '')}"
                for r in search_results
            ]
        )

        messages = self.build_messages(
            f"""
        Task:
        {task['description']}

        Search Results:
        {results_text}

        Create a structured research summary.
        """
        )

        response = await self.llm.ainvoke(messages)
        updated_tasks = state.get("tasks",[])
        for t in updated_tasks:
            if t["id"] == task["id"]:
                t["status"] = "done"

        finding = {
            "task_id": task["id"],
            "task_title": task["title"],
            "summary": response.content,
            "sources": [
                r.get("url")
                for r in search_results
                if r.get("url")
            ],
        }
        remaining = [
            t
            for t in updated_tasks
            if t.get("agent") == "researcher"
            and t.get("status") == "pending"
        ]

        next_agent = (
            "researcher"
            if remaining
            else "architect"
        )
        return {
            "messages": [
                AIMessage(
                    content=f"[Researcher] Completed: {task['title']}"
                )
            ],
            "tasks": updated_tasks,
            "research_findings": state.get(
                "research_findings",
                []
            )
            + [finding],
            "next_agent": next_agent,
        }