"""Structured outputs the agents ask the LLM for.

`with_structured_output` turns these into tool/JSON-schema calls, so every
provider returns validated objects instead of free text we have to parse.
"""

from pydantic import BaseModel, Field


class SearchPlan(BaseModel):
    """Targeted news searches that together cover the reader's topic."""

    queries: list[str] = Field(description="Distinct, specific web search queries, most important first.")


class CuratedSources(BaseModel):
    """The articles worth reading for the topic, and the best photo to run with them."""

    urls: list[str] = Field(
        description="URLs of the relevant articles, copied exactly from the candidate list, most relevant first. "
        "Return an empty list if none of them are actually about the topic."
    )
    image_url: str = Field(
        description="URL of the candidate image that best illustrates the story, copied exactly. "
        "Empty string if none is a good editorial photo (logos, charts of other things, screenshots, ads)."
    )


class ArticleDraft(BaseModel):
    """A finished newspaper article."""

    title: str = Field(description="A concise, compelling headline. No citation markers.")
    summary: str = Field(description="A two-sentence summary for the front page. No citation markers.")
    paragraphs: list[str] = Field(
        description="The article body: 4 to 6 well-developed paragraphs. Cite sources inline like [1] or [2][3]."
    )
    highlight: str = Field(
        description="The most striking sentence from the middle or end of your article (never the opening "
        "sentence), reused verbatim as a pull quote. No citation markers."
    )


class ArticleRevision(ArticleDraft):
    """A revised article plus a note back to the critic."""

    message: str = Field(description="A short note to the critic explaining what you changed, or why you didn't.")


class Critique(BaseModel):
    """An editor's verdict on an article."""

    approved: bool = Field(description="True if the article is ready to publish as is.")
    feedback: str = Field(description="Short, actionable feedback for the writer. Empty when approved.")


class IllustrationBrief(BaseModel):
    """An art director's commission for the story's illustration."""

    prompt: str = Field(
        description="2-4 sentences describing one striking visual metaphor or scene for the story: concrete "
        "objects, setting and composition. No real, identifiable people (use silhouettes or symbols), no text."
    )
    alt_text: str = Field(description="Concise alt text describing the illustration for screen readers.")


class EditorsNote(BaseModel):
    """A short note from the editor-in-chief that opens the edition."""

    note: str = Field(description="Two or three warm, crisp sentences tying today's stories together.")
