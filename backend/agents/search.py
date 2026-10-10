import asyncio
from functools import lru_cache

from langchain_core.tools import ToolException
from langchain_tavily import TavilySearch
from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..state import ArticleState, Image, Source
from .common import emit, widen

MAX_CANDIDATES = 15


@lru_cache(maxsize=32)
def get_search_tool(time_range: str | None, api_key: str | None = None) -> TavilySearch:
    kwargs = {"tavily_api_key": api_key} if api_key else {}
    return TavilySearch(
        topic="news",
        max_results=8,
        time_range=time_range,
        include_raw_content="text",  # full article text, so writers aren't working from snippets
        include_images=True,
        include_image_descriptions=True,  # lets the curator pick a photo that fits the story
        include_favicon=True,
        **kwargs,
    )


def _is_web_url(url: str | None) -> bool:
    # These URLs end up in hrefs and img srcs, so never let e.g. javascript: through
    return bool(url) and url.startswith(("https://", "http://"))


async def _search(query: str, time_range: str | None, api_key: str | None = None) -> dict:
    try:
        response = await get_search_tool(time_range, api_key).ainvoke({"query": query})
    except ToolException:
        # langchain-tavily raises when there are no results
        return {"results": [], "images": []}
    if "error" in response:
        raise RuntimeError(f"Tavily search failed: {response['error']}")
    return response


async def _search_all(queries: list[str], time_range: str | None, api_key: str | None) -> list[dict]:
    return await asyncio.gather(*(_search(q, time_range, api_key) for q in queries))


def _merge(responses: list[dict]) -> tuple[list[Source], list[Image]]:
    """Merge results from several searches, deduping by URL and keeping the best score."""
    sources: dict[str, Source] = {}
    images: dict[str, Image] = {}
    for response in responses:
        for r in response.get("results", []):
            url = r.get("url")
            if not _is_web_url(url):
                continue
            if url in sources and sources[url].get("score", 0) >= (r.get("score") or 0):
                continue
            sources[url] = {
                "title": r.get("title") or "",
                "url": url,
                "content": r.get("content") or "",
                "raw_content": r.get("raw_content") or "",
                "score": r.get("score") or 0.0,
                "published_date": r.get("published_date") or "",
                "favicon": r.get("favicon") if _is_web_url(r.get("favicon")) else "",
            }
        for img in response.get("images", []):
            image: Image = (
                {"url": img}
                if isinstance(img, str)
                else {"url": img.get("url"), "description": img.get("description") or ""}
            )
            if _is_web_url(image["url"]):
                images.setdefault(image["url"], image)
    ranked = sorted(sources.values(), key=lambda s: s.get("score", 0), reverse=True)
    return ranked[:MAX_CANDIDATES], list(images.values())[:10]


async def search_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    ctx = runtime.context
    queries = state.get("queries") or [state["query"]]
    time_range = state.get("time_range", ctx.news_time_range)
    state = {**state, "time_range": time_range}
    if not state.get("retry_search"):
        emit(state, "search", "Searching the news")

    candidates, images = _merge(await _search_all(queries, time_range, ctx.tavily_api_key))
    update = {"candidates": candidates, "images": images, "time_range": time_range, "retry_search": False}
    if candidates:
        outlets = len({s["url"].split("/")[2] for s in candidates})
        emit(state, "search", f"Found {len(candidates)} stories from {outlets} outlets")
    elif retry := widen(state, f"Quiet {time_range or 'news cycle'}"):
        update |= retry
    else:
        emit(state, "skipped", "No news found for this topic")
    return update
