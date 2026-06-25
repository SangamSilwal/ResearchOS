
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from core.config import settings


async def main():
    client = MultiServerMCPClient(
        {
            "github": {
                "url": "https://api.githubcopilot.com/mcp/",
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {settings.github_token}"},
            },
        }
    )

    tools = await client.get_tools()
    print(f"--- {len(tools)} tools discovered on GitHub MCP server ---")
    for t in tools:
        print(f"  - {t.name}")

    search_tool = next(
        (t for t in tools if t.name in ("search_repositories", "search_repos")),
        None,
    )
    if search_tool is None:
        print("\n!! No search_repositories/search_repos tool found.")
        print("   This means the token's toolset doesn't expose repo search,")
        print("   or the tool name differs in your server version (see list above).")
        return

    print(f"\n--- calling {search_tool.name} ---")
    raw = await search_tool.ainvoke({"query": "langchain", "perPage": 3})

    print(f"\nraw response type: {type(raw)}")
    print(f"raw response repr (first 1000 chars):\n{repr(raw)[:1000]}")


if __name__ == "__main__":
    asyncio.run(main())