from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..prompts import ASSIGNMENT_PROMPT
from ..schemas import SearchPlan
from ..state import ArticleState
from .common import chat_model, emit, today


async def assignment_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    """Turn the reader's topic into a few targeted news searches."""
    ctx = runtime.context
    query = state["query"]
    if ctx.searches_per_topic <= 1:
        return {"queries": [query]}

    emit(state, "plan", "Planning the coverage")
    plan: SearchPlan = await (ASSIGNMENT_PROMPT | chat_model(ctx, SearchPlan)).ainvoke(
        {
            "today": today(),
            "query": query,
            "count": ctx.searches_per_topic,
        }
    )
    # Dedupe case-insensitively, keep the model's priority order
    unique: dict[str, str] = {}
    for q in plan.queries:
        if q.strip():
            unique.setdefault(q.strip().lower(), q.strip())
    queries = list(unique.values())
    queries = queries[: ctx.searches_per_topic] or [query]
    emit(state, "plan", "Assigned: " + " · ".join(f"“{q}”" for q in queries))
    return {"queries": queries}
