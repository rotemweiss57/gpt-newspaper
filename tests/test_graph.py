from pathlib import Path

import pytest

from backend.agents import NoArticlesError
from backend.config import NewspaperContext
from backend.graph import graph, stream_newspaper


def context(tmp_path, **overrides) -> NewspaperContext:
    return NewspaperContext(model="fake:model", output_dir=str(tmp_path), **overrides)


async def test_full_run_writes_newspaper_and_articles(tmp_path, fake_llm, fake_search):
    state = await graph.ainvoke(
        {"topics": ["AI chips", "nothing here", "space"], "layout": "layout_3"},
        context=context(tmp_path, max_revisions=2, sources_per_article=3),
    )

    articles = state["articles"]
    # The topic with no news is skipped, the rest come back in topic order
    assert [a["query"] for a in sorted(articles, key=lambda a: a["index"])] == ["AI chips", "space"]
    for article in articles:
        assert article["revisions"] == 1
        assert article["title"] == "Revised <b>headline</b>"
        assert article["paragraphs"] == ["New p1", "New p2"]
        # Curator drops hallucinated URLs and keeps the model's pick
        assert [s["url"] for s in article["sources"]][0].startswith("https://news3.example.com/")
        assert all("hallucinated" not in s["url"] for s in article["sources"])
        assert (tmp_path / article["path"]).exists()

    newspaper = Path(state["newspaper_path"]).read_text()
    assert "Revised &lt;b&gt;headline&lt;/b&gt;" in newspaper  # LLM output is escaped
    assert "<b>headline</b>" not in newspaper
    # search retried without a time range for the empty topic
    assert ("nothing here", None) in fake_search


async def test_revision_budget_stops_the_loop(tmp_path, fake_llm, fake_search):
    await graph.ainvoke(
        {"topics": ["markets"], "layout": "layout_1"}, context=context(tmp_path, max_revisions=0)
    )
    assert "Critique" not in fake_llm.calls
    assert "ArticleRevision" not in fake_llm.calls


async def test_all_topics_empty_raises(tmp_path, fake_llm, fake_search):
    with pytest.raises(NoArticlesError):
        await graph.ainvoke({"topics": ["nothing here"], "layout": "layout_2"}, context=context(tmp_path))


async def test_stream_emits_progress_then_done(tmp_path, fake_llm, fake_search, monkeypatch):
    import backend.graph as graph_module

    monkeypatch.setattr(graph_module, "OUTPUTS_DIR", tmp_path)
    events = [e async for e in stream_newspaper(["robots", "oceans", "nothing here"], "layout_2", context(tmp_path / "run"))]

    stages = [e["stage"] for e in events if e["type"] == "progress"]
    for stage in ["search", "curate", "write", "review", "design", "done", "skipped", "edit", "publish"]:
        assert stage in stages
    # Articles from parallel branches are merged by the reducer, not overwritten
    assert events[-1] == {"type": "done", "url": "/outputs/run/newspaper.html", "articles": 2}
