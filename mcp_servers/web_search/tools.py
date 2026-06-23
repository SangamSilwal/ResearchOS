import os
from tavily import TavilyClient

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(api_key=TAVILY_API_KEY)

async def search(query: str, max_results: int = 5):

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_answer=True,
        include_raw_content=False,
    )

    return {
        "answer": response.get("answer"),
        "results": response.get("results", []),
    }



async def fetch(url: str):
    response = client.extract(urls=[url])

    return {
        "url": url,
        "content": response.get("results", []),
    }

async def deep_search(query: str):
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=7,
        include_answer=True,
        include_raw_content=True,
    )

    return {
        "summary": response.get("answer"),
        "results": response.get("results", []),
    }
