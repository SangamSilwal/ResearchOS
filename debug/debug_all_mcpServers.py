import asyncio
import json
from langchain_mcp_adapters.client import MultiServerMCPClient
from core.config import settings


QUERY = "FastAPI best practices"


async def main():
    client = MultiServerMCPClient(
        {
            "web_search": {
                "url": "http://localhost:8000/mcp",
                "transport": "streamable_http",
            },
            "arxiv_search": {
                "url": "http://localhost:8001/mcp",
                "transport": "streamable_http",
            },
            "github": {
                "url": "https://api.githubcopilot.com/mcp/",
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {settings.github_token}"},
            },
        }
    )

    tools = await client.get_tools()
    tools_by_name = {t.name: t for t in tools}
    print(f"--- {len(tools)} total tools discovered ---")
    for name in tools_by_name:
        print(f"  - {name}")
    print()

    def dump(label: str, raw):
        print(f"=== {label} ===")
        print(f"type: {type(raw)}")
        print(f"repr (first 800 chars):\n{repr(raw)[:800]}")
        print()

    # --- web_search ---
    if "web_search" in tools_by_name:
        try:
            raw = await tools_by_name["web_search"].ainvoke(
                {"query": QUERY, "max_results": 5}
            )
            dump("web_search", raw)
        except Exception as e:
            print(f"=== web_search ERROR: {type(e).__name__}: {e} ===\n")
    else:
        print("=== web_search tool NOT FOUND in discovered tools ===\n")

    # --- arxiv_search ---
    if "arxiv_search" in tools_by_name:
        try:
            raw = await tools_by_name["arxiv_search"].ainvoke(
                {"query": QUERY, "max_results": 5}
            )
            dump("arxiv_search", raw)
        except Exception as e:
            print(f"=== arxiv_search ERROR: {type(e).__name__}: {e} ===\n")
    else:
        print("=== arxiv_search tool NOT FOUND in discovered tools ===\n")

    # --- github search_repositories ---
    if "search_repositories" in tools_by_name:
        try:
            raw = await tools_by_name["search_repositories"].ainvoke(
                {"query": QUERY, "perPage": 5}
            )
            dump("github search_repositories", raw)
        except Exception as e:
            print(f"=== github ERROR: {type(e).__name__}: {e} ===\n")
    else:
        print("=== search_repositories tool NOT FOUND in discovered tools ===\n")


if __name__ == "__main__":
    asyncio.run(main())