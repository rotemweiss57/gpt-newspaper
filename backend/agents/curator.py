from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..prompts import CURATOR_PROMPT
from ..schemas import CuratedSources
from ..state import ArticleState
from .common import chat_model, emit, format_images, format_sources, today, widen


async def curator_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    """Keep only sources that are really about the topic, and pick the photo."""
    ctx = runtime.context
    candidates, images = state["candidates"], state.get("images", [])
    emit(state, "curate", f"Reading {len(candidates)} stories, keeping the best")

    result: CuratedSources = await (CURATOR_PROMPT | chat_model(ctx, CuratedSources)).ainvoke(
        {
            "today": today(),
            "query": state["query"],
            "candidates": format_sources(candidates),
            "images": format_images(images),
            "count": ctx.sources_per_article,
        }
    )

    # Keep the model's ranking, but only trust URLs that really came from the search
    by_url = {c["url"]: c for c in candidates}
    chosen = [by_url[url] for url in dict.fromkeys(result.urls) if url in by_url][: ctx.sources_per_article]
    if result.urls and not chosen:
        # The model answered but mangled every URL: fall back to search ranking
        chosen = candidates[: ctx.sources_per_article]

    image_urls = {img["url"] for img in images}
    image = result.image_url if result.image_url in image_urls else ""

    if chosen:
        emit(state, "curate", f"Kept {len(chosen)} of {len(candidates)} stories")
        return {"sources": chosen, "image": image}
    if retry := widen(state, "Nothing on-topic yet"):
        return {"sources": [], **retry}
    emit(state, "skipped", "Nothing in the news is really about this topic yet")
    return {"sources": []}
