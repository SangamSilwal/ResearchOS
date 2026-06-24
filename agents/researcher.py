import asyncio
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings
from langsmith.run_helpers import traceable

class ResearcherAgent(BaseAgent):

    def __init__(self):
        super().__init__(settings.researcher_model)
        self.mcp_client = MultiServerMCPClient(
            {
                "web_search": {
                    "url":"http://localhost:8000/mcp",
                    "transport":"streamable_http",
                },
                "arxiv_search":{
                    "url":"http://localhost:8001/mcp",
                    "transport":"streamable_http"
                }
            }
        )

        self.web_search_tool = None
        self.arxiv_tool = None

    async def initialize(self):
        tools = await self.mcp_client.get_tools()
        tools_by_name = {tool.name: tool for tool in tools}
        self.web_search_tool = tools_by_name["web_search"]
        self.arxiv_tool = tools_by_name["arxiv_search"]

    def system_prompt(self) -> str:
        return """
        You are the Researcher agent of ResearchOS.
        You receive search results, academic papers,
        You receive search results and synthesize them into clear,
        structured findings.

        For each topic:
        - Extract the most important facts and insights
        - Note best practices and recommendations
        - Identify tools, frameworks, and concepts
        - Flag contradictory or outdated information
        - Cite relevant arXiv papers if they materially inform the answer

        Be concise but complete.
        Use clear sections and bullet points.
        """
    
    @traceable(name="web_search")
    async def _search_web(self, query: str, max_results: int = 5) -> list[dict]:
        try:
            results = await self.web_search_tool.ainvoke(
                {"query": query, "max_results": max_results}
            )
            return results or []
        except Exception as e:
            return [{"url": None, "content": f"[web_search error: {e}]"}]
    @traceable(name="arxiv_search")
    async def _search_arxiv(self, query: str, max_results: int = 5) -> list[dict]:
        try:
            results = await self.arxiv_tool.ainvoke(
                {"query": query, "max_results": max_results}
            )
            return results or []
        except Exception as e:
            return [{"url": None, "content": f"[arxiv error: {e}]"}]
    

    @staticmethod
    def _format_arxiv(results: list[dict]) -> str:
        if not results:
            return "(no arxiv results)"
        blocks = []
        for r in results:
            if r.get("title") is None:
                blocks.append(r.get("content", ""))
                continue
            authors = ", ".join(r.get("authors", [])[:4])
            blocks.append(
                f"Paper: {r.get('title')}\n"
                f"Authors: {authors}\n"
                f"Published: {r.get('published')}\n"
                f"URL: {r.get('url')}\n"
                f"Abstract: {r.get('content', '')}"
            )
        return "\n\n".join(blocks)
    
    @staticmethod
    def _format_web(results: list[dict]) -> str:
        if not results:
            return "(no web results)"
        return "\n\n".join(
            f"Source: {r.get('url', 'unknown')}\n{r.get('content', '')}"
            for r in results
        )
    @traceable(name="researcher_agent")
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

        web_results, arxiv_results = await asyncio.gather(
            self._search_web(query,max_results=5),
            self._search_arxiv(query,max_results=5)
        )
        prompt = f"""
        Task:
        {task['description']}
 
        Web Search Results:
        {self._format_web(web_results)}
 
        ArXiv Paper Results:
        {self._format_arxiv(arxiv_results)}
 
        Create a structured research summary that draws on all two
        sources above. Call out which findings come from papers vs. general web sources where it matters.
        """


        messages = self.build_messages(prompt)
        response = await self.llm.ainvoke(messages)

        updated_tasks = state.get("tasks",[])
        for t in updated_tasks:
            if t["id"] == task["id"]:
                t["status"] = "done"

         
        all_sources = (
            [r.get("url") for r in web_results if r.get("url")]
            + [r.get("url") for r in arxiv_results if r.get("url")]
        )

        finding = {
            "task_id": task["id"],
            "task_title": task["title"],
            "summary": response.content,
            "sources": all_sources
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