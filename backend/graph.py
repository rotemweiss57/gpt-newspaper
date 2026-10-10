"""The GPT Newspaper LangGraph.

START ─┬─ Send(topic 1) ─► [reporter] ─┐
       ├─ Send(topic 2) ─► [reporter] ─┼─► editor ─► publisher ─► END
       └─ Send(topic N) ─► [reporter] ─┘

reporter (one article subgraph per topic, all in parallel):
    assignment ─► search ─► curator ─► writer ─► critique ─► illustrator ─► designer
                   ▲  │          │         ▲          │
                   └──┴─widen────┘         └─revise───┘
                 (nothing relevant: look further back, then give up)
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import RetryPolicy, Send

from .agents import (
    assignment_node,
    critique_node,
    curator_node,
    designer_node,
    editor_node,
    illustrator_node,
    publisher_node,
    route_after_critique,
    search_node,
    writer_node,
)
from .config import NewspaperContext, public_url
from .state import ArticleState, Layout, NewspaperState

logger = logging.getLogger(__name__)

# Retry transient failures (rate limits, timeouts, 5xx) on every node that calls an API
API_RETRY = RetryPolicy(max_attempts=3, initial_interval=1.0)


def route_after_search(state: ArticleState) -> str:
    if state.get("candidates"):
        return "curate"
    return "widen" if state.get("retry_search") else "skip"


def route_after_curator(state: ArticleState) -> str:
    if state.get("sources"):
        return "write"
    return "widen" if state.get("retry_search") else "skip"


def build_article_graph():
    builder = StateGraph(ArticleState, context_schema=NewspaperContext)
    builder.add_node("assignment", assignment_node, retry_policy=API_RETRY)
    builder.add_node("search", search_node, retry_policy=API_RETRY)
    builder.add_node("curator", curator_node, retry_policy=API_RETRY)
    builder.add_node("writer", writer_node, retry_policy=API_RETRY)
    builder.add_node("critique", critique_node, retry_policy=API_RETRY)
    builder.add_node("illustrator", illustrator_node, retry_policy=API_RETRY)
    builder.add_node("designer", designer_node)

    builder.add_edge(START, "assignment")
    builder.add_edge("assignment", "search")
    builder.add_conditional_edges("search", route_after_search, {"curate": "curator", "widen": "search", "skip": END})
    builder.add_conditional_edges("curator", route_after_curator, {"write": "writer", "widen": "search", "skip": END})
    builder.add_edge("writer", "critique")
    builder.add_conditional_edges("critique", route_after_critique, {"revise": "writer", "approve": "illustrator"})
    builder.add_edge("illustrator", "designer")
    builder.add_edge("designer", END)
    return builder.compile(name="article")


article_graph = build_article_graph()


async def reporter_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    """Run one topic's article subgraph. A failing story is reported, but never sinks the whole edition."""
    try:
        result = await article_graph.ainvoke(state, context=runtime.context)
        return {"articles": result.get("articles", [])}
    except Exception as e:
        logger.warning("Story %r failed", state.get("query"), exc_info=True)
        message = f"{type(e).__name__}: {e}"
        get_stream_writer()(
            {
                "topic": state.get("query"),
                "index": state.get("index"),
                "stage": "failed",
                "message": f"This story didn't make it: {message}",
            }
        )
        return {"failures": [message]}


def assign_reporters(state: NewspaperState) -> list[Send]:
    """Fan out: every topic gets its own reporter, all working in parallel."""
    return [
        Send("reporter", {"query": topic, "index": i, "layout": state.get("layout")})
        for i, topic in enumerate(state["topics"])
    ]


def build_newspaper_graph():
    builder = StateGraph(NewspaperState, context_schema=NewspaperContext)
    builder.add_node("reporter", reporter_node)
    builder.add_node("editor", editor_node)
    builder.add_node("publisher", publisher_node)

    builder.add_conditional_edges(START, assign_reporters, ["reporter"])
    builder.add_edge("reporter", "editor")
    builder.add_edge("editor", "publisher")
    builder.add_edge("publisher", END)
    return builder.compile(name="gpt-newspaper")


# Exported for LangGraph Studio / `langgraph dev` (see langgraph.json)
graph = build_newspaper_graph()


async def stream_newspaper(
    topics: list[str], layout: Layout, context: NewspaperContext | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Run the newsroom, yielding progress events and finally {"type": "done", "url": ...}."""
    context = context or NewspaperContext()
    final_state: dict[str, Any] = {}

    async for namespace, mode, data in graph.astream(
        {"topics": topics, "layout": layout},
        context=context,
        stream_mode=["custom", "values"],
        subgraphs=True,
    ):
        if mode == "custom":
            yield {"type": "progress", **data}
        elif mode == "values" and not namespace:
            # The parent graph's full state, with reducers applied
            final_state = data

    yield {
        "type": "done",
        "url": public_url(final_state["newspaper_path"]),
        "articles": len(final_state.get("articles", [])),
        "failed": len(final_state.get("failures", [])),
    }
