import pytest
from fastapi.staticfiles import StaticFiles
from langchain_core.runnables import RunnableLambda

import backend.config as config
import backend.server as server
from backend.agents import common, illustrator, search
from backend.schemas import (
    ArticleDraft,
    ArticleRevision,
    Critique,
    CuratedSources,
    EditorsNote,
    IllustrationBrief,
    SearchPlan,
)

OFF_TOPIC = "celebrity gossip"  # search finds results, but the curator rejects them all
NO_NEWS = "nothing here"  # search finds nothing at all
EXPLODES = "explodes"  # the writer crashes on this topic


def make_results(query: str, n: int = 6) -> dict:
    slug = query.replace(" ", "-")
    return {
        "results": [
            {
                "title": f"{query} story {i}",
                "url": f"https://news{i}.example.com/{slug}",
                "content": f"Facts about {query} #{i}",
                "raw_content": f"The full text about {query} #{i}",
                "score": 1 - i / 10,
                "favicon": f"https://news{i}.example.com/favicon.ico",
            }
            for i in range(n)
        ]
        + [{"title": "evil", "url": "javascript:alert(1)", "content": "x"}],
        "images": [
            {"url": "https://img.example.com/logo.png", "description": "A company logo"},
            {"url": f"https://img.example.com/{slug}.jpg", "description": f"Photo of {query}"},
        ],
    }


def _topic(prompt: str) -> str:
    line = next(line for line in prompt.splitlines() if line.startswith("Reader's topic: "))
    return line.removeprefix("Reader's topic: ")


class FakeLLM:
    """Stands in for any LangChain chat model: answers structured-output calls by schema."""

    def __init__(self):
        self.calls: list[str] = []
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            text = prompt_value.to_string()
            self.calls.append(schema.__name__)
            self.prompts.append(text)
            if schema is EditorsNote:
                return EditorsNote(note="Today: <b>big</b> news.")
            if schema is IllustrationBrief:
                return IllustrationBrief(prompt="A lighthouse made of circuit boards.", alt_text="A circuit lighthouse")
            topic = _topic(text)
            slug = topic.replace(" ", "-")
            if schema is SearchPlan:
                return SearchPlan(queries=[f"{topic} latest", f"{topic} latest", f"{topic} analysis"])
            if schema is CuratedSources:
                if topic == OFF_TOPIC:
                    return CuratedSources(urls=[], image_url="")
                return CuratedSources(
                    urls=[
                        "https://hallucinated.example.com",
                        f"https://news3.example.com/{slug}",
                        f"https://news1.example.com/{slug}",
                    ],
                    image_url=f"https://img.example.com/{slug}.jpg",
                )
            if schema is ArticleRevision:
                return ArticleRevision(
                    title="Revised <b>headline</b>",
                    summary="Better [1].",
                    paragraphs=["New p1 [1].", " ", "New p2 [2, 9].", "p3 <script>x</script>", "p4"],
                    highlight="A striking line.",
                    message="Tightened the lede",
                )
            if schema is ArticleDraft:
                if topic == EXPLODES:
                    raise RuntimeError("model exploded")
                return ArticleDraft(
                    title="Draft", summary="Two sentences.", paragraphs=["p1 [1]", "p2", "p3"], highlight="h"
                )
            if schema is Critique:
                if "Note from the writer" not in text:
                    return Critique(approved=False, feedback="Lead with the news.")
                return Critique(approved=True, feedback="")
            raise AssertionError(schema)

        return RunnableLambda(respond)


@pytest.fixture(autouse=True)
def outputs_dir(tmp_path, monkeypatch):
    out = tmp_path / "outputs"
    out.mkdir()
    monkeypatch.setattr(config, "OUTPUTS_DIR", out)
    monkeypatch.setattr(server, "OUTPUTS_DIR", out)
    for route in server.app.routes:
        if getattr(route, "name", None) == "outputs":
            monkeypatch.setattr(route, "app", StaticFiles(directory=out))
    return out


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(common, "get_chat_model", lambda *a, **k: llm)
    return llm


@pytest.fixture(autouse=True)
def fake_images(monkeypatch):
    """Never call a real image API in tests. Records every request."""
    calls = []

    async def generate_image(model, prompt, size, api_key, quality="medium"):
        calls.append({"model": model, "prompt": prompt, "size": size, "api_key": api_key})
        if "FAIL" in prompt:
            raise RuntimeError("content policy")
        return b"RIFF-fake-webp"

    monkeypatch.setattr(illustrator, "generate_image", generate_image)
    return calls


@pytest.fixture
def fake_search(monkeypatch):
    calls = []

    async def _search(query, time_range, api_key=None):
        calls.append((query, time_range, api_key))
        if query.startswith(NO_NEWS):
            return {"results": [], "images": []}
        return make_results(query.removesuffix(" latest").removesuffix(" analysis"))

    monkeypatch.setattr(search, "_search", _search)
    return calls
