from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..llm import get_chat_model
from ..prompts import REVISE_PROMPT, WRITER_PROMPT
from ..schemas import ArticleDraft, ArticleRevision
from ..state import ArticleState
from .common import emit, format_article, format_sources, today


def _clean_paragraphs(paragraphs: list[str]) -> list[str]:
    return [p.strip() for p in paragraphs if p and p.strip()]


async def write(state: ArticleState, ctx: NewspaperContext) -> dict:
    emit(state, "write", "Drafting the article")
    llm = get_chat_model(ctx.model, ctx.temperature).with_structured_output(ArticleDraft)
    draft: ArticleDraft = await (WRITER_PROMPT | llm).ainvoke({
        "today": today(),
        "query": state["query"],
        "sources": format_sources(state["sources"]),
    })
    return {
        "title": draft.title.strip(),
        "summary": draft.summary.strip(),
        "paragraphs": _clean_paragraphs(draft.paragraphs),
        "revisions": 0,
    }


async def revise(state: ArticleState, ctx: NewspaperContext) -> dict:
    revision_number = state.get("revisions", 0) + 1
    emit(state, "write", f"Revising the article (round {revision_number})")
    llm = get_chat_model(ctx.model, ctx.temperature).with_structured_output(ArticleRevision)
    revision: ArticleRevision = await (REVISE_PROMPT | llm).ainvoke({
        "today": today(),
        "query": state["query"],
        "sources": format_sources(state["sources"]),
        "article": format_article(state),
        "critique": state["critique"],
    })
    emit(state, "write", f"Writer: {revision.message}")
    return {
        "title": revision.title.strip() or state["title"],
        "summary": revision.summary.strip() or state["summary"],
        "paragraphs": _clean_paragraphs(revision.paragraphs) or state["paragraphs"],
        "writer_note": revision.message,
        "critique": None,
        "revisions": revision_number,
    }


async def writer_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    if state.get("critique"):
        return await revise(state, runtime.context)
    return await write(state, runtime.context)
