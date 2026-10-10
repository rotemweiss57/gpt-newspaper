from langgraph.config import get_stream_writer

from ..rendering import render
from ..state import NewspaperState
from .common import today


class NoArticlesError(RuntimeError):
    pass


def editor_node(state: NewspaperState) -> dict:
    articles = sorted(state.get("articles", []), key=lambda a: a.get("index", 0))
    if not articles:
        raise NoArticlesError("No news was found for any of your topics. Try broader topics.")

    get_stream_writer()({"stage": "edit", "message": f"Putting {len(articles)} {'story' if len(articles) == 1 else 'stories'} on the page"})
    html = render(f"newspaper/{state['layout']}.html", articles=articles, date=today())
    return {"newspaper_html": html}
