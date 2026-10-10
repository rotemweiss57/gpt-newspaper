import re
from datetime import datetime

from langgraph.config import get_stream_writer

from ..config import NewspaperContext
from ..llm import get_chat_model
from ..state import ArticleState, Image, Source

SNIPPET_CHARS = 1_000
# Writers share one full-text budget: a lone long source gets far more room than one of five
FULL_TEXT_BUDGET = 30_000
FULL_TEXT_PER_SOURCE = (4_000, 20_000)


# When nothing relevant turns up, reporters look further back in time before giving up
WIDER_TIME_RANGE = {"day": "week", "week": "month", "month": "year"}
MAX_WIDENINGS = 2


def widen(state: ArticleState, reason: str) -> dict | None:
    """State update that sends the reporter back out with a wider time range, or None if it can't."""
    current = state.get("time_range")
    wider = WIDER_TIME_RANGE.get(current or "")
    if not wider or state.get("widenings", 0) >= MAX_WIDENINGS:
        return None
    emit(state, "search", f"{reason}: digging into the past {wider}")
    return {"time_range": wider, "widenings": state.get("widenings", 0) + 1, "retry_search": True}


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w]+", "-", text.lower()).strip("-")
    return slug[:60] or "article"


def today() -> str:
    now = datetime.now()
    return f"{now:%A, %B} {now.day}, {now.year}"


def chat_model(ctx: NewspaperContext, schema):
    """The run's chat model, constrained to return `schema`."""
    return get_chat_model(ctx.model, ctx.temperature, ctx.api_key).with_structured_output(schema)


def emit(state: ArticleState, stage: str, message: str, **extra) -> None:
    """Stream a progress event for one topic to whoever is listening (UI, CLI, Studio)."""
    get_stream_writer()(
        {
            "topic": state.get("query"),
            "index": state.get("index"),
            "stage": stage,
            "message": message,
            **extra,
        }
    )


def format_sources(sources: list[Source], full_text: bool = False) -> str:
    """Numbered sources for prompts. Writers get the full article text; curators get snippets."""
    low, high = FULL_TEXT_PER_SOURCE
    limit = max(low, min(high, FULL_TEXT_BUDGET // max(len(sources), 1))) if full_text else SNIPPET_CHARS
    blocks = []
    for i, s in enumerate(sources, 1):
        text = (s.get("raw_content") if full_text else None) or s.get("content") or ""
        published = f"Published: {s['published_date']}\n" if s.get("published_date") else ""
        blocks.append(f"[{i}] {s.get('title') or 'Untitled'}\nURL: {s['url']}\n{published}{text[:limit].strip()}")
    return "\n\n".join(blocks)


def format_images(images: list[Image]) -> str:
    if not images:
        return "(none)"
    return "\n".join(
        f"- {img['url']}" + (f" | {img['description']}" if img.get("description") else "") for img in images
    )


def format_article(state: ArticleState) -> str:
    body = "\n\n".join(state.get("paragraphs", []))
    return f"Headline: {state.get('title', '')}\nSummary: {state.get('summary', '')}\n\n{body}"
