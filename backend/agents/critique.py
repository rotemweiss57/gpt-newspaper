from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..prompts import CRITIQUE_PROMPT
from ..schemas import Critique
from ..state import ArticleState
from .common import chat_model, emit, format_article, format_sources, today


async def critique_node(state: ArticleState, runtime: Runtime[NewspaperContext]) -> dict:
    ctx = runtime.context
    if state.get("revisions", 0) >= ctx.max_revisions:
        # Revision budget spent: ship it rather than loop forever
        emit(state, "review", "Approved for print")
        return {"critique": None}

    emit(state, "review", "The editor is fact-checking the draft")
    writer_note = state.get("writer_note")
    review: Critique = await (CRITIQUE_PROMPT | chat_model(ctx, Critique)).ainvoke(
        {
            "today": today(),
            "language": ctx.language,
            "query": state["query"],
            "sources": format_sources(state["sources"], full_text=True),
            "article": format_article(state),
            "writer_note": f"\nNote from the writer about their last revision: {writer_note}\n" if writer_note else "",
        }
    )

    feedback = review.feedback.strip()
    if review.approved or not feedback:
        emit(state, "review", "Approved for print")
        return {"critique": None}

    emit(state, "review", f"Editor: {feedback}")
    return {"critique": feedback}


def route_after_critique(state: ArticleState) -> str:
    return "revise" if state.get("critique") else "approve"
