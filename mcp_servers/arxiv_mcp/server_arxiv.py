import os
import arxiv
from mcp.server.fastmcp import FastMCP

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "5051"))

mcp = FastMCP("arxiv_search", host=HOST, port=PORT)
_client = arxiv.Client()

@mcp.tool()
def arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    max_results = max(1,min(max_results,25))
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    results = []
    try:
        for result in _client.results(search):
            results.append(
                {
                    "url":result.entry_id,
                    "title":result.title,
                    "authors":[a.name for a in result.authors],
                    "published": str(result.published.date()),
                    "content":result.summary.replace("/n"," ").strip(),
                }
            )
    except Exception as e:
        results.append({
            "url":None,
            "title":None,
            "content":f"arxiv error: {e}"
        })
    return results

if __name__ == "__main__":
    mcp.run(transport="streamable-http")