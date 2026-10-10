import math
import os

from langgraph.runtime import Runtime

from ..config import NewspaperContext, public_url
from ..rendering import render, strip_citations
from ..state import Article, ArticleState
from .common import emit, slugify, today

WORDS_PER_MINUTE = 230


def _normalize(text: str) -> str:
    return " ".join(strip_citations(text).lower().split())


def pull_quote_position(paragraphs: list[str], highlight: str) -> int | None:
    """Where to run the pull quote: never right next to the paragraph it was pulled from."""
    if not highlight or len(paragraphs) < 4:
        return None
    key = _normalize(highlight)[:60]
    source = next((i for i, p in enumerate(paragraphs) if key and key in _normalize(p)), None)
    if source is None or source >= 3:
        return 2  # after the second paragraph
    position = source + 3
    return position if position < len(paragraphs) else None


def asset_url(output_dir: str, src: str) -> str:
    """Absolute URL for an image: remote photos as-is, generated illustrations via /outputs."""
    if not src or src.startswith(("https://", "http://")):
        return src
    return public_url(os.path.join(output_dir, src))


async def designer_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    ctx = runtime.context
    emit(state, "design", "Laying out the page")
    words = sum(len(strip_citations(p).split()) for p in state["paragraphs"])
    path = f"{state.get('index', 0) + 1:02d}-{slugify(state['query'])}.html"
    article: Article = {
        "query": state["query"],
        "index": state.get("index", 0),
        "title": state["title"],
        "summary": state["summary"],
        "paragraphs": state["paragraphs"],
        "highlight": state.get("highlight", ""),
        "pull_quote_at": pull_quote_position(state["paragraphs"], state.get("highlight", "")),
        "image": state.get("image", ""),
        "image_alt": state.get("image_alt", ""),
        "illustrated": state.get("illustrated", False),
        "sources": state["sources"],
        "date": today(),
        "revisions": state.get("revisions", 0),
        "reading_minutes": max(1, math.ceil(words / WORDS_PER_MINUTE)),
        "path": path,
        "url": public_url(os.path.join(ctx.output_dir, path)),
    }

    os.makedirs(ctx.output_dir, exist_ok=True)
    with open(os.path.join(ctx.output_dir, path), "w", encoding="utf-8") as f:
        f.write(render("article.html", article=article, model=ctx.model, image_model=ctx.image_model, page=ctx.page))

    preview = {key: article[key] for key in ("title", "summary", "url", "reading_minutes")}
    preview["image"] = asset_url(ctx.output_dir, article["image"])
    emit(state, "done", "On the front page", article=preview)
    return {"articles": [article]}
