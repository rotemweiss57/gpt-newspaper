import operator
from typing import Annotated, Literal, TypedDict

Layout = Literal["layout_1", "layout_2", "layout_3"]


class Source(TypedDict, total=False):
    title: str
    url: str
    content: str
    score: float
    published_date: str


class Article(TypedDict, total=False):
    query: str
    index: int
    title: str
    summary: str
    paragraphs: list[str]
    image: str
    sources: list[Source]
    date: str
    path: str
    revisions: int


class ArticleState(TypedDict, total=False):
    """State of the per-topic subgraph: search -> curate -> write <-> critique -> design."""

    query: str
    index: int
    candidates: list[Source]
    image: str
    sources: list[Source]
    title: str
    summary: str
    paragraphs: list[str]
    critique: str | None
    writer_note: str | None
    revisions: int
    # The only key handed back to the parent graph
    articles: list[Article]


class ArticleOutput(TypedDict):
    articles: list[Article]


class NewspaperState(TypedDict, total=False):
    topics: list[str]
    layout: Layout
    # Every topic subgraph appends its finished article here, in parallel
    articles: Annotated[list[Article], operator.add]
    newspaper_html: str
    newspaper_path: str
