import os
import re

from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..rendering import render
from ..state import Article, ArticleState
from .common import emit, today


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "article"


async def designer_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    emit(state, "design", "Laying out the article")
    article: Article = {
        "query": state["query"],
        "index": state.get("index", 0),
        "title": state["title"],
        "summary": state["summary"],
        "paragraphs": state["paragraphs"],
        "image": state["image"],
        "sources": state["sources"],
        "date": today(),
        "revisions": state.get("revisions", 0),
        "path": f"{state.get('index', 0) + 1:02d}-{_slugify(state['query'])}.html",
    }

    output_dir = runtime.context.output_dir
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, article["path"]), "w", encoding="utf-8") as f:
        f.write(render("article.html", article=article))

    emit(state, "done", "Ready")
    return {"articles": [article]}
