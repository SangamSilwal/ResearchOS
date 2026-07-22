import os
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from . import tools

load_dotenv()

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "5050"))

mcp = FastMCP("web-search-mcp", host=HOST, port=PORT)



@mcp.tool()
async def web_search(query: str, max_results: int = 5):
    return await tools.search(query, max_results)


@mcp.tool()
async def fetch_url(url: str):
    return await tools.fetch(url)


@mcp.tool()
async def deep_research(query: str):
    return await tools.deep_search(query)



if __name__ == "__main__":
    mcp.run(transport="streamable-http")