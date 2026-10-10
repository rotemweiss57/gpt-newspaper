from functools import lru_cache

from langchain_core.tools import ToolException
from langchain_tavily import TavilySearch
from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..state import ArticleState, Source
from .common import emit

FALLBACK_IMAGE = (
    "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1600&q=80"
)


@lru_cache
def get_search_tool(time_range: str | None) -> TavilySearch:
    return TavilySearch(
        topic="news",
        max_results=10,
        include_images=True,
        time_range=time_range,
    )


def _is_web_url(url: str | None) -> bool:
    # These URLs end up in hrefs and img srcs, so never let e.g. javascript: through
    return bool(url) and url.startswith(("https://", "http://"))


async def _search(query: str, time_range: str | None) -> dict:
    try:
        response = await get_search_tool(time_range).ainvoke({"query": query})
    except ToolException:
        # langchain-tavily raises when there are no results
        return {"results": [], "images": []}
    if "error" in response:
        raise RuntimeError(f"Tavily search failed: {response['error']}")
    return response


async def search_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    query = state["query"]
    time_range = runtime.context.news_time_range
    emit(state, "search", f"Searching the news for “{query}”")

    response = await _search(query, time_range)
    if not response.get("results") and time_range:
        emit(state, "search", f"Nothing in the last {time_range}, widening the search")
        response = await _search(query, None)

    candidates: list[Source] = [
        {
            "title": r.get("title", ""),
            "url": r["url"],
            "content": r.get("content", ""),
            "score": r.get("score", 0.0),
            "published_date": r.get("published_date", ""),
        }
        for r in response.get("results", [])
        if _is_web_url(r.get("url"))
    ]
    images = [img if isinstance(img, str) else img.get("url") for img in response.get("images", [])]
    image = next((img for img in images if _is_web_url(img)), FALLBACK_IMAGE)

    if candidates:
        emit(state, "search", f"Found {len(candidates)} stories")
    else:
        emit(state, "skipped", "No news found for this topic")
    return {"candidates": candidates, "image": image}
