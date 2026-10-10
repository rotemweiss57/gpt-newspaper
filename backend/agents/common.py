from datetime import datetime

from langgraph.config import get_stream_writer

from ..state import ArticleState, Source

MAX_SOURCE_CHARS = 2000


def today() -> str:
    now = datetime.now()
    return f"{now:%A, %B} {now.day}, {now.year}"


def emit(state: ArticleState, stage: str, message: str) -> None:
    """Stream a progress event for one topic to whoever is listening (UI, Studio, CLI)."""
    get_stream_writer()({
        "topic": state.get("query"),
        "index": state.get("index"),
        "stage": stage,
        "message": message,
    })


def format_sources(sources: list[Source]) -> str:
    return "\n\n".join(
        f"[{i}] {s.get('title', 'Untitled')}\n"
        f"URL: {s['url']}\n"
        + (f"Published: {s['published_date']}\n" if s.get("published_date") else "")
        + (s.get("content") or "")[:MAX_SOURCE_CHARS]
        for i, s in enumerate(sources, 1)
    )


def format_article(state: ArticleState) -> str:
    body = "\n\n".join(state.get("paragraphs", []))
    return f"Headline: {state.get('title', '')}\nSummary: {state.get('summary', '')}\n\n{body}"
