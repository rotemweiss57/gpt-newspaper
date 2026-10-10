from backend.rendering import cite, strip_citations


def test_cite_links_known_sources_only():
    html = cite("Chips are up [1][2, 7]. <b>bold</b> [x]", source_count=2)
    assert html.count('<sup class="cite">') == 2
    assert "#source-7" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "[x]" in html


def test_strip_citations():
    assert strip_citations("A claim [1]. Another [2, 3].") == "A claim. Another."


def test_pull_quote_is_never_next_to_its_source():
    from backend.agents.designer import pull_quote_position

    paragraphs = ["Lede sentence here [1].", "Two.", "Three.", "Four.", "Five."]
    assert pull_quote_position(paragraphs, "Lede sentence here.") == 3  # after paragraph 3, two away from the lede
    assert pull_quote_position(paragraphs, "Five.") == 2
    assert pull_quote_position(paragraphs, "Not in the article") == 2
    assert pull_quote_position(paragraphs[:3], "Two.") is None  # too short for a pull quote
    assert pull_quote_position(["A", "B quote", "C", "D"], "B quote") is None  # nowhere far enough away
