import re
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

CITATION = re.compile(r"\s?\[(\d+(?:\s*,\s*\d+)*)\]")


def domain(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.")


def strip_citations(text: str) -> str:
    return CITATION.sub("", text or "")


def cite(text: str, source_count: int) -> Markup:
    """Escape the text, then turn [1] / [2, 3] markers into links to the numbered sources."""

    def link(match: re.Match) -> str:
        numbers = [int(n) for n in re.findall(r"\d+", match.group(1))]
        return "".join(
            f'<sup class="cite"><a href="#source-{n}" aria-label="Source {n}">{n}</a></sup>'
            for n in numbers
            if 1 <= n <= source_count
        )

    # Escaping first means only our own <sup> markup can ever reach the page
    return Markup(CITATION.sub(link, str(escape(text or ""))))  # noqa: S704 (input escaped above)


_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    # LLM output and web content end up in these pages, so always escape
    autoescape=select_autoescape(default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters.update(domain=domain, cite=cite, strip_citations=strip_citations)


def render(template: str, **context) -> str:
    return _env.get_template(template).render(**context)
