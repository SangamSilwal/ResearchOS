import asyncio
import json
import os
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings
from langsmith.run_helpers import traceable
from core.memory import get_recent_runs

class ResearcherAgent(BaseAgent):

    def __init__(self):
        super().__init__(settings.researcher_model)
        web_search_url = os.getenv("MCP_WEB_SEARCH_URL", "http://localhost:8000/mcp")
        arxiv_url = os.getenv("MCP_ARXIV_URL", "http://localhost:8001/mcp")
        self.mcp_client = MultiServerMCPClient(
            {
                "web_search": {
                    "url": web_search_url,
                    "transport":"streamable_http",
                },
                "arxiv_search":{
                    "url": arxiv_url,
                    "transport":"streamable_http"
                },
                "github": {
                    "url": "https://api.githubcopilot.com/mcp/",
                    "transport": "streamable_http",
                    "headers": {
                        "Authorization": f"Bearer {settings.github_token}"
                    },
                },

            }
        )

        self.web_search_tool = None
        self.arxiv_tool = None
        self.github_search_tool = None

    async def initialize(self):
        tools = await self.mcp_client.get_tools()
        tools_by_name = {tool.name: tool for tool in tools}
        self.web_search_tool = tools_by_name["web_search"]
        self.arxiv_tool = tools_by_name["arxiv_search"]
        self.github_search_tool = next(
            (
                tool
                for name, tool in tools_by_name.items()
                if name in ("search_repositories","search_repos")
            ),
            None,
        )
        if self.github_search_tool is None:
            raise RuntimeError(
                "Could not find a repository-search tool on the GitHub "
                "MCP server. Run mcp_client.get_tools() and inspect "
                "tool names — they may differ by server version/toolset."
            )


    def system_prompt(self) -> str:
        return """
        You are the Researcher agent of ResearchOS.
        You receive search results, academic papers, and code repository
        data, then synthesize them into clear, structured findings.
 
        For each topic:
        - Extract the most important facts and insights
        - Note best practices and recommendations
        - Identify tools, frameworks, and concepts
        - Cite GitHub repos/implementations if genuinely useful
        - Flag contradictory or outdated information
 
        ArXiv papers: many topics (especially software engineering,
        frameworks, and tools) have no real academic coverage. If the
        retrieved arXiv papers are not substantively about the task
        topic, do NOT cite them or attempt to draw a connection -- say
        plainly that no relevant academic papers were found. Never
        stretch an unrelated paper's subject matter into a tenuous
        "lesson" just because it was retrieved.
 
        Be concise but complete.
        Use clear sections and bullet points.
        """

    
    # Shared MCP response Unwrapped
    @staticmethod
    def _unwrap_mcp_text(raw):
        if (isinstance(raw,list) and raw and isinstance(raw[0],dict) and "text" in raw[0] and "type" in raw[0]):
            return json.loads(raw[0]["text"])
        if isinstance(raw,str):
            return json.loads(raw)
        if isinstance(raw, (list,dict)):
            return raw
        raise TypeError(f"Unrecognized MCP tool response type: {type(raw)}")


    @traceable(name="web_search")
    async def _search_web(self, query: str, max_results: int = 5) -> list[dict]:
        try:
            raw = await self.web_search_tool.ainvoke(
                {"query": query, "max_results": max_results}
            )
            parsed = self._unwrap_mcp_text(raw)
            results = (
                parsed.get("results",[]) if isinstance(parsed,dict) else parsed
            )
            if not results:
                return [
                    {
                        "url":None,
                        "content":f"[web_search: 0 results parsed from response: {str(parsed)[:300]}]",
                    }
                ]
            return results[:max_results]
        except Exception as e:
            return [{"url": None, "content": f"[web_search error: {type(e).__name__}: {e}]"}]



    @traceable(name="arxiv_search")
    async def _search_arxiv(self, query: str, max_results: int = 5) -> list[dict]:
        try:
            raw = await self.arxiv_tool.ainvoke(
                {"query": query, "max_results": max_results}
            )
            parsed = self._unwrap_mcp_text(raw)
            if isinstance(parsed, dict):
                results = [parsed]
            else:
                results = parsed or []
            if not results:
                return [
                    {
                        "url":None,
                        "content":f"[arxiv: 0 results parsed from response: {str(parsed)[:300]}]",
                    }
                ]
            return results[:max_results]
        except Exception as e:
            return [{"url": None, "content": f"[arxiv error: {type(e).__name__} : {e}]"}]
        
    @traceable(name="github_search")
    async def _search_github(self, query: str, max_results: int = 5) -> list[dict]:
        try:
            raw = await self.github_search_tool.ainvoke(
                {"query": query, "perPage": max_results}
            )
            parsed = self._unwrap_mcp_text(raw)
            items = parsed.get("items", []) if isinstance(parsed, dict) else parsed
 
            if not items:
                return [
                    {
                        "url": None,
                        "title": None,
                        "content": f"[github: 0 results parsed from response: {str(parsed)[:300]}]",
                    }
                ]
 
            normalized = []
            for repo in items[:max_results]:
                normalized.append(
                    {
                        "url": repo.get("html_url") or repo.get("url"),
                        "title": repo.get("full_name") or repo.get("name"),
                        "stars": repo.get("stargazers_count") or repo.get("stars"),
                        "content": (repo.get("description") or "").strip(),
                    }
                )
            return normalized
        except Exception as e:
            return [{"url": None, "title": None, "content": f"[github error: {type(e).__name__}: {e}]"}]
 
    
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

     
    @staticmethod
    def _format_github(results: list[dict]) -> str:
        if not results:
            return "(no github results)"
        blocks = []
        for r in results:
            if r.get("title") is None:
                blocks.append(r.get("content", ""))
                continue
            blocks.append(
                f"Repo: {r.get('title')} (\u2605 {r.get('stars', 0)})\n"
                f"URL: {r.get('url')}\n"
                f"Description: {r.get('content', '')}"
            )
        return "\n\n".join(blocks)


    @traceable(name="researcher_agent")
    async def run(self, state: ResearchState) -> dict:
        research_tasks = [
            t
            for t in state.get("tasks",[])
            if t.get("agent") == "researcher" and t.get("status") == "pending"
        ]

        if not research_tasks:

            has_pending_architect_tasks = any(
                t.get("agent") == "architect" and t.get("status") == "pending"
                for t in state.get("tasks",[])
            )

            has_pending_coder_tasks = any(
                t.get("agent") == "coder" and t.get("status") == "pending"
                for t in state.get("tasks", [])
            )

            has_pending_planner_tasks = any(
                t.get("agent") == "planner" and t.get("status") == "pending"
                for t in state.get("tasks",[])
            )

            if has_pending_architect_tasks or has_pending_coder_tasks:
                fallback_next = "architect"
            elif has_pending_planner_tasks:
                fallback_next = "planner"
            else:
                fallback_next = "done"

            return {
                "messages":[
                    AIMessage(
                        content="[Researcher] No pending research tasks"
                    )
                ],
                "next_agent":fallback_next
            }
        task = research_tasks[0]
        query = f"{state['goal']} - {task['description']}"
        github_query = task.get("title") or task.get("description")

        web_results, arxiv_results,github_results = await asyncio.gather(
            self._search_web(query,max_results=5),
            self._search_arxiv(query,max_results=5),
            self._search_github(github_query, max_results=5),
        )

        prompt = f"""
        Task:
        {task['description']}
 
        Web Search Results:
        {self._format_web(web_results)}
 
        ArXiv Paper Results:
        {self._format_arxiv(arxiv_results)}
 
        GitHub Repository Results:
        {self._format_github(github_results)}
 
        Create a structured research summary that draws on all three
        sources above. Call out which findings come from papers vs.
        code vs. general web sources where it matters.
 
        IMPORTANT: only cite an arXiv paper or GitHub repo if it is
        genuinely relevant to the task topic. If the ArXiv Paper
        Results are absent, empty, or clearly unrelated to the topic
        (e.g. a software/engineering topic with no real academic
        coverage), explicitly state that no relevant academic papers
        were found rather than forcing a tenuous connection. Do not
        manufacture relevance that isn't there.
        """


        recent_runs = await get_recent_runs(n=3)
        messages = self.build_messages(prompt,state=state,recent_runs=recent_runs)
        response = await self.llm.ainvoke(messages)

        updated_tasks = state.get("tasks",[])
        for t in updated_tasks:
            if t["id"] == task["id"]:
                t["status"] = "done"

         
        all_sources = (
            [r.get("url") for r in web_results if r.get("url")]
            + [r.get("url") for r in arxiv_results if r.get("url")]
            + [r.get("url") for r in github_results if r.get("url")]
        )


        finding = {
            "task_id": task["id"],
            "task_title": task["title"],
            "summary": response.content,
            "sources": all_sources
        }

        remaining_researcher = [
            t
            for t in updated_tasks
            if t.get("agent") == "researcher" and t.get("status") == "pending"
        ]
 
        if remaining_researcher:
            next_agent = "researcher"
        else:
            has_pending_architect_task = any(
                t.get("agent") == "architect" and t.get("status") == "pending"
                for t in updated_tasks
            )
            has_pending_coder_tasks = any(
                t.get("agent") == "coder" and t.get("status") == "pending"
                for t in updated_tasks
            )
            has_pending_planner_tasks = any(
                t.get("agent") == "planner" and t.get("status") == "pending"
                for t in updated_tasks
            )
            if has_pending_architect_task or has_pending_coder_tasks:
                next_agent = "architect"
            elif has_pending_planner_tasks:
                next_agent = "planner"
            else:
                next_agent = "done"

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