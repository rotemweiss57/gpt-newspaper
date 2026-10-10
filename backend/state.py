import operator
from typing import Annotated, Literal, TypedDict

Layout = Literal["layout_1", "layout_2", "layout_3"]


class Source(TypedDict, total=False):
    title: str
    url: str
    content: str
    raw_content: str
    score: float
    published_date: str
    favicon: str


class Image(TypedDict, total=False):
    url: str
    description: str


class Article(TypedDict, total=False):
    query: str
    index: int
    image_alt: str
    illustrated: bool
    title: str
    summary: str
    paragraphs: list[str]
    highlight: str
    pull_quote_at: int | None
    image: str
    sources: list[Source]
    date: str
    path: str
    url: str
    reading_minutes: int
    revisions: int


class ArticleState(TypedDict, total=False):
    """State of one reporter's assignment: plan -> search -> curate -> write <-> critique -> design."""

    query: str
    index: int
    layout: Layout
    queries: list[str]
    time_range: str | None
    widenings: int
    retry_search: bool
    candidates: list[Source]
    images: list[Image]
    image: str
    image_alt: str
    illustrated: bool
    sources: list[Source]
    title: str
    summary: str
    paragraphs: list[str]
    highlight: str
    critique: str | None
    writer_note: str | None
    revisions: int
    articles: list[Article]


class NewspaperState(TypedDict, total=False):
    topics: list[str]
    layout: Layout
    # Every reporter appends to these in parallel; the reducer merges them
    articles: Annotated[list[Article], operator.add]
    failures: Annotated[list[str], operator.add]
    editors_note: str
    newspaper_html: str
    newspaper_path: str
