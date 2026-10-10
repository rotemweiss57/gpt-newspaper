import json
from pathlib import Path

import pytest

from backend.agents import NoArticlesError
from backend.config import NewspaperContext
from backend.graph import graph, stream_newspaper

from .conftest import EXPLODES, NO_NEWS, OFF_TOPIC


def context(outputs_dir, **overrides) -> NewspaperContext:
    return NewspaperContext(model="fake:model", output_dir=str(outputs_dir / "run"), **overrides)


async def test_illustrations_in_house_style_sized_per_slot(outputs_dir, fake_llm, fake_search, fake_images):
    ctx = context(outputs_dir, image_style="engraving", image_api_key="sk-img")
    events = [e async for e in stream_newspaper(["robots", "oceans"], "layout_3", ctx)]
    assert sorted(c["size"] for c in fake_images) == ["1536x1024", "1536x960"]  # grid story + front-page lead
    assert all("engraving" in c["prompt"].lower() and "No likenesses" in c["prompt"] for c in fake_images)
    assert {c["api_key"] for c in fake_images} == {"sk-img"}

    run = outputs_dir / "run"
    assert (run / "01-robots.webp").read_bytes() == b"RIFF-fake-webp"
    front = (run / "newspaper.html").read_text()
    assert 'class="figure illustration"' in front and 'alt="A circuit lighthouse"' in front
    assert "AI illustration" in (run / "01-robots.html").read_text()
    previews = [e["article"] for e in events if e.get("article")]
    assert {p["image"] for p in previews} == {"/outputs/run/01-robots.webp", "/outputs/run/02-oceans.webp"}
    edition = json.loads((run / "edition.json").read_text())
    assert edition["articles"][0]["image"] == "/outputs/run/01-robots.webp"


async def test_illustration_failures_fall_back_to_the_news_photo(outputs_dir, fake_llm, fake_search, monkeypatch):
    from backend import images

    monkeypatch.setattr(images, "HOUSE_RULES", "FAIL")
    ctx = context(outputs_dir, image_style="ink", image_api_key="k")
    state = await graph.ainvoke({"topics": ["robots"], "layout": "layout_1"}, context=ctx)
    [article] = state["articles"]
    assert article["image"] == "https://img.example.com/robots.jpg" and not article["illustrated"]


async def test_no_image_key_uses_news_photos(outputs_dir, fake_llm, fake_search, fake_images, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ctx = context(outputs_dir, image_style="ink")
    await graph.ainvoke({"topics": ["robots"], "layout": "layout_1"}, context=ctx)
    assert fake_images == []


async def test_full_edition(outputs_dir, fake_llm, fake_search):
    state = await graph.ainvoke(
        {"topics": ["AI chips", NO_NEWS, "space", OFF_TOPIC], "layout": "layout_3"},
        context=context(outputs_dir, max_revisions=2, sources_per_article=3, tavily_api_key="tvly-user"),
    )

    articles = sorted(state["articles"], key=lambda a: a["index"])
    # No-news and off-topic topics are dropped; the rest come back in topic order
    assert [a["query"] for a in articles] == ["AI chips", "space"]
    for article in articles:
        assert article["revisions"] == 1
        assert article["paragraphs"] == ["New p1 [1].", "New p2 [2, 9].", "p3 <script>x</script>", "p4"]
        # Curator: model ranking kept, hallucinated URL dropped, chosen photo used
        assert [s["url"].split("/")[2] for s in article["sources"]] == ["news3.example.com", "news1.example.com"]
        assert article["image"].endswith(article["query"].replace(" ", "-") + ".jpg")
        assert article["url"] == f"/outputs/run/{article['path']}"
        assert (outputs_dir / "run" / article["path"]).exists()

    # The user's Tavily key is used for every search, and javascript: URLs never survive
    assert {call[2] for call in fake_search} == {"tvly-user"}
    assert all(s["url"].startswith("https://") for a in articles for s in a["sources"])
    # Planner queries are deduped
    assert ("AI chips latest", "week", "tvly-user") in fake_search
    assert sum(1 for q, *_ in fake_search if q == "AI chips latest") == 1


async def test_pages_are_escaped_and_cited(outputs_dir, fake_llm, fake_search):
    await graph.ainvoke({"topics": ["robots"], "layout": "layout_1"}, context=context(outputs_dir))
    run = outputs_dir / "run"
    newspaper = (run / "newspaper.html").read_text()
    article = (run / "01-robots.html").read_text()

    assert "Revised &lt;b&gt;headline&lt;/b&gt;" in newspaper
    assert "Today: &lt;b&gt;big&lt;/b&gt; news." in newspaper  # editor's note
    assert "<script>x</script>" not in article and "&lt;script&gt;" in article
    # [1] links to source 1; [2, 9] links only the sources that exist
    assert '<a href="#source-1"' in article and '<a href="#source-2"' in article
    assert "#source-9" not in article
    assert '<blockquote class="pull-quote">A striking line.</blockquote>' in article
    assert 'property="og:title"' in article


async def test_edition_metadata(outputs_dir, fake_llm, fake_search):
    await graph.ainvoke(
        {"topics": ["robots", "oceans"], "layout": "layout_2"}, context=context(outputs_dir, language_code="he")
    )
    edition = json.loads((outputs_dir / "run" / "edition.json").read_text())
    assert edition["topics"] == ["robots", "oceans"]
    assert edition["language"] == "he" and edition["model"] == "fake:model"
    assert edition["url"] == "/outputs/run/newspaper.html"
    assert len(edition["articles"]) == 2
    assert 'dir="rtl"' in (outputs_dir / "run" / "newspaper.html").read_text()
    assert any("Write everything in Hebrew" in p for p in fake_llm.prompts)


async def test_off_topic_results_make_the_reporter_dig_further_back(outputs_dir, fake_llm, fake_search):
    events = [e async for e in stream_newspaper(["robots", OFF_TOPIC], "layout_1", context(outputs_dir))]
    ranges = [time_range for query, time_range, _ in fake_search if query.startswith(OFF_TOPIC)]
    # 2 planned queries per attempt: this week, then the past month, then the past year, then give up
    assert ranges == ["week"] * 2 + ["month"] * 2 + ["year"] * 2
    messages = [e["message"] for e in events if e.get("topic") == OFF_TOPIC]
    assert "Nothing on-topic yet: digging into the past month" in messages
    assert messages[-1].startswith("Nothing in the news")


async def test_no_results_widen_the_search(outputs_dir, fake_llm, fake_search):
    with pytest.raises(NoArticlesError):
        await graph.ainvoke({"topics": [NO_NEWS]}, context=context(outputs_dir, news_time_range="month"))
    assert [r for _, r, _ in fake_search] == ["month", "month", "year", "year"]


async def test_revision_budget_stops_the_loop(outputs_dir, fake_llm, fake_search):
    await graph.ainvoke({"topics": ["markets"], "layout": "layout_1"}, context=context(outputs_dir, max_revisions=0))
    assert "Critique" not in fake_llm.calls and "ArticleRevision" not in fake_llm.calls


async def test_single_search_skips_the_planner(outputs_dir, fake_llm, fake_search):
    await graph.ainvoke(
        {"topics": ["markets"], "layout": "layout_1"}, context=context(outputs_dir, searches_per_topic=1)
    )
    assert "SearchPlan" not in fake_llm.calls
    assert [q for q, *_ in fake_search] == ["markets"]


async def test_a_failing_story_does_not_sink_the_edition(outputs_dir, fake_llm, fake_search):
    events = [e async for e in stream_newspaper(["robots", EXPLODES], "layout_1", context(outputs_dir))]
    assert any(e.get("stage") == "failed" and "model exploded" in e["message"] for e in events)
    assert events[-1]["type"] == "done" and events[-1]["articles"] == 1 and events[-1]["failed"] == 1


async def test_all_failed_reports_the_cause(outputs_dir, fake_llm, fake_search):
    with pytest.raises(NoArticlesError, match="model exploded"):
        await graph.ainvoke({"topics": [EXPLODES], "layout": "layout_1"}, context=context(outputs_dir))


async def test_nothing_found(outputs_dir, fake_llm, fake_search):
    with pytest.raises(NoArticlesError, match="No news"):
        await graph.ainvoke({"topics": [NO_NEWS, OFF_TOPIC], "layout": "layout_2"}, context=context(outputs_dir))


async def test_stream_emits_progress_then_done(outputs_dir, fake_llm, fake_search):
    events = [e async for e in stream_newspaper(["robots", "oceans", NO_NEWS], "layout_2", context(outputs_dir))]

    stages = [e["stage"] for e in events if e["type"] == "progress"]
    for stage in ["plan", "search", "curate", "write", "review", "design", "done", "skipped", "edit", "publish"]:
        assert stage in stages
    previews = [e["article"] for e in events if e.get("stage") == "done"]
    assert {p["url"] for p in previews} == {"/outputs/run/01-robots.html", "/outputs/run/02-oceans.html"}
    # Articles from parallel branches are merged by the reducer, not overwritten
    assert events[-1] == {"type": "done", "url": "/outputs/run/newspaper.html", "articles": 2, "failed": 0}
    assert Path(outputs_dir / "run" / "newspaper.html").exists()


def test_cli(outputs_dir, fake_llm, fake_search, monkeypatch, capsys):
    import backend.setup as setup
    from backend.cli import main

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(setup, "get_chat_model", lambda *a, **k: fake_llm)
    assert main(["robots", "--layout", "front", "--model", "ollama:llama3.1", "--quiet"]) == 0
    path = capsys.readouterr().out.strip()
    assert path.endswith("newspaper.html") and Path(path).exists()


def test_cli_reports_setup_errors(monkeypatch, capsys):
    from backend.cli import main

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert main(["robots"]) == 1
    assert "Tavily API key" in capsys.readouterr().err
