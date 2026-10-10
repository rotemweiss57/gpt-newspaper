import pytest
from langchain_core.runnables import RunnableLambda

from backend.agents import critique, curator, search, writer
from backend.schemas import ArticleDraft, ArticleRevision, CuratedSources, Critique


def make_results(query: str, n: int = 8) -> dict:
    return {
        "results": [
            {
                "title": f"{query} story {i}",
                "url": f"https://news{i}.example.com/{query.replace(' ', '-')}",
                "content": f"Facts about {query} #{i}",
                "score": 1 - i / 10,
            }
            for i in range(n)
        ],
        "images": ["https://img.example.com/photo.jpg"],
    }


class FakeLLM:
    """Stands in for any LangChain chat model: answers structured-output calls by schema."""

    def __init__(self, reject_first_draft: bool = True):
        self.calls: list[str] = []
        self.reject_first_draft = reject_first_draft

    def with_structured_output(self, schema):
        def respond(prompt_value):
            text = prompt_value.to_string()
            self.calls.append(schema.__name__)
            if schema is CuratedSources:
                return CuratedSources(urls=["https://hallucinated.example.com", "https://news3.example.com/" + _topic(text)])
            if schema is ArticleRevision:
                return ArticleRevision(title="Revised <b>headline</b>", summary="Better.", paragraphs=["New p1", " ", "New p2"], message="Tightened the lede")
            if schema is ArticleDraft:
                return ArticleDraft(title="<script>alert(1)</script> Draft", summary="Two sentences.", paragraphs=["p1", "p2", "p3"])
            if schema is Critique:
                first_review = "Note from the writer" not in text
                if self.reject_first_draft and first_review:
                    return Critique(approved=False, feedback="Lead with the news.")
                return Critique(approved=True, feedback="")
            raise AssertionError(schema)

        return RunnableLambda(respond)


def _topic(prompt: str) -> str:
    line = next(l for l in prompt.splitlines() if l.startswith("Topic: "))
    return line.removeprefix("Topic: ").replace(" ", "-")


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()
    for module in (curator, writer, critique):
        monkeypatch.setattr(module, "get_chat_model", lambda *a, **k: llm)
    return llm


@pytest.fixture
def fake_search(monkeypatch):
    empty_topics = {"nothing here"}
    calls = []

    async def _search(query, time_range):
        calls.append((query, time_range))
        if query in empty_topics:
            return {"results": [], "images": []}
        return make_results(query)

    monkeypatch.setattr(search, "_search", _search)
    return calls
