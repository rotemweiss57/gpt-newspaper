from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..prompts import REVISE_PROMPT, WRITER_PROMPT
from ..schemas import ArticleDraft, ArticleRevision
from ..state import ArticleState
from .common import chat_model, emit, format_article, format_sources, today


def _clean(paragraphs: list[str]) -> list[str]:
    return [p.strip() for p in paragraphs if p and p.strip()]


async def write(state: ArticleState, ctx: NewspaperContext) -> dict:
    count = len(state["sources"])
    emit(state, "write", f"Drafting from {count} {'source' if count == 1 else 'sources'}")
    draft: ArticleDraft = await (WRITER_PROMPT | chat_model(ctx, ArticleDraft)).ainvoke(
        {
            "today": today(),
            "language": ctx.language,
            "query": state["query"],
            "sources": format_sources(state["sources"], full_text=True),
        }
    )
    return {
        "title": draft.title.strip(),
        "summary": draft.summary.strip(),
        "paragraphs": _clean(draft.paragraphs),
        "highlight": draft.highlight.strip(),
        "revisions": 0,
    }


async def revise(state: ArticleState, ctx: NewspaperContext) -> dict:
    revision_number = state.get("revisions", 0) + 1
    emit(state, "write", f"Revising the draft (round {revision_number})")
    revision: ArticleRevision = await (REVISE_PROMPT | chat_model(ctx, ArticleRevision)).ainvoke(
        {
            "today": today(),
            "language": ctx.language,
            "query": state["query"],
            "sources": format_sources(state["sources"], full_text=True),
            "article": format_article(state),
            "critique": state["critique"],
        }
    )
    emit(state, "write", f"Writer: {revision.message}")
    return {
        "title": revision.title.strip() or state["title"],
        "summary": revision.summary.strip() or state["summary"],
        "paragraphs": _clean(revision.paragraphs) or state["paragraphs"],
        "highlight": revision.highlight.strip() or state.get("highlight", ""),
        "writer_note": revision.message,
        "critique": None,
        "revisions": revision_number,
    }


async def writer_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    if state.get("critique"):
        return await revise(state, runtime.context)
    return await write(state, runtime.context)
