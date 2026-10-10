"""Structured outputs the agents ask the LLM for.

Using `with_structured_output` with these models replaces the old
"please return nothing but JSON" prompting, and works across providers.
"""

from pydantic import BaseModel, Field


class CuratedSources(BaseModel):
    """The articles worth reading for the topic, most relevant first."""

    urls: list[str] = Field(description="URLs copied exactly from the candidate list, most relevant first.")


class ArticleDraft(BaseModel):
    """A finished newspaper article."""

    title: str = Field(description="A concise, compelling headline.")
    summary: str = Field(description="A two-sentence summary for the newspaper front page.")
    paragraphs: list[str] = Field(description="The article body: 4 to 6 well-developed paragraphs.")


class ArticleRevision(ArticleDraft):
    """A revised article plus a note back to the critic."""

    message: str = Field(description="A short note to the critic explaining what you changed, or why you didn't.")


class Critique(BaseModel):
    """An editor's verdict on an article."""

    approved: bool = Field(description="True if the article is ready to publish as is.")
    feedback: str = Field(description="Short, actionable feedback for the writer. Empty when approved.")
