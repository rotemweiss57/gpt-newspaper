"""The GPT Newspaper LangGraph.

    START ─┬─ Send(topic 1) ─► [article subgraph] ─┐
           ├─ Send(topic 2) ─► [article subgraph] ─┼─► editor ─► publisher ─► END
           └─ Send(topic N) ─► [article subgraph] ─┘

    article subgraph:
        search ─► curator ─► writer ─► critique ─► designer
                     │          ▲          │
                     │          └─revise───┘
                     └─(no news found)─► END
"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .agents import (
    critique_node,
    curator_node,
    designer_node,
    editor_node,
    publisher_node,
    route_after_critique,
    search_node,
    writer_node,
)
from .config import OUTPUTS_DIR, NewspaperContext
from .state import ArticleOutput, ArticleState, Layout, NewspaperState


def build_article_graph():
    builder = StateGraph(ArticleState, context_schema=NewspaperContext, output_schema=ArticleOutput)
    builder.add_node("search", search_node)
    builder.add_node("curator", curator_node)
    builder.add_node("writer", writer_node)
    builder.add_node("critique", critique_node)
    builder.add_node("designer", designer_node)

    builder.add_edge(START, "search")
    builder.add_conditional_edges(
        "search", lambda s: "curate" if s.get("candidates") else "skip", {"curate": "curator", "skip": END}
    )
    builder.add_edge("curator", "writer")
    builder.add_edge("writer", "critique")
    builder.add_conditional_edges("critique", route_after_critique, {"revise": "writer", "approve": "designer"})
    builder.add_edge("designer", END)
    return builder.compile(name="article")


def assign_reporters(state: NewspaperState) -> list[Send]:
    """Fan out: every topic gets its own article subgraph, all running in parallel."""
    return [Send("article", {"query": topic, "index": i}) for i, topic in enumerate(state["topics"])]


def build_newspaper_graph():
    builder = StateGraph(NewspaperState, context_schema=NewspaperContext)
    builder.add_node("article", build_article_graph())
    builder.add_node("editor", editor_node)
    builder.add_node("publisher", publisher_node)

    builder.add_conditional_edges(START, assign_reporters, ["article"])
    builder.add_edge("article", "editor")
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

    path = Path(final_state["newspaper_path"]).resolve()
    yield {
        "type": "done",
        "url": "/outputs/" + path.relative_to(OUTPUTS_DIR.resolve()).as_posix(),
        "articles": len(final_state.get("articles", [])),
    }
