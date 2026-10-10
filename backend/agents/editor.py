import logging

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..prompts import EDITORS_NOTE_PROMPT
from ..rendering import render
from ..schemas import EditorsNote
from ..state import NewspaperState
from .common import chat_model, today

logger = logging.getLogger(__name__)


class NoArticlesError(RuntimeError):
    pass


async def _editors_note(articles, ctx: NewspaperContext) -> str:
    stories = "\n".join(f"- {a['title']}: {a['summary']}" for a in articles)
    try:
        result: EditorsNote = await (EDITORS_NOTE_PROMPT | chat_model(ctx, EditorsNote)).ainvoke(
            {
                "today": today(),
                "language": ctx.language,
                "stories": stories,
            }
        )
        return result.note.strip()
    except Exception:
        # A missing editor's note should never cost the reader their newspaper
        logger.warning("Could not write the editor's note", exc_info=True)
        return ""


async def editor_node(state: NewspaperState, runtime: Runtime[NewspaperContext]) -> dict:
    ctx = runtime.context
    articles = sorted(state.get("articles", []), key=lambda a: a.get("index", 0))
    if not articles:
        failures = state.get("failures", [])
        if failures:
            raise NoArticlesError(f"Every story failed. First error: {failures[0]}")
        raise NoArticlesError("No news was found for any of your topics. Try broader or more newsworthy topics.")

    write = get_stream_writer()
    write({"stage": "edit", "message": "The editor-in-chief is writing today's note"})
    note = await _editors_note(articles, ctx)

    count = len(articles)
    write({"stage": "edit", "message": f"Putting {count} {'story' if count == 1 else 'stories'} on the front page"})
    html = render(
        f"newspaper/{state['layout']}.html",
        articles=articles,
        date=today(),
        editors_note=note,
        model=ctx.model,
        page=ctx.page,
    )
    return {"newspaper_html": html, "editors_note": note}
