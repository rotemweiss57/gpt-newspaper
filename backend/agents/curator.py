from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..llm import get_chat_model
from ..prompts import CURATOR_PROMPT
from ..schemas import CuratedSources
from ..state import ArticleState
from .common import emit, format_sources, today


async def curator_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    ctx = runtime.context
    candidates = state["candidates"]
    count = ctx.sources_per_article

    if len(candidates) <= count:
        emit(state, "curate", f"Keeping all {len(candidates)} sources")
        return {"sources": candidates}

    emit(state, "curate", f"Picking the best {count} of {len(candidates)} sources")
    llm = get_chat_model(ctx.model, ctx.temperature).with_structured_output(CuratedSources)
    chain = CURATOR_PROMPT | llm
    result: CuratedSources = await chain.ainvoke({
        "today": today(),
        "query": state["query"],
        "candidates": format_sources(candidates),
        "count": count,
    })

    # Keep the model's ranking, but only trust URLs that really came from the search
    by_url = {c["url"]: c for c in candidates}
    chosen = [by_url[url] for url in dict.fromkeys(result.urls) if url in by_url][:count]
    if not chosen:
        chosen = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)[:count]

    return {"sources": chosen}
