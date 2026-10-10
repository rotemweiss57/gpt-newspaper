from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape


def domain(url: str) -> str:
    host = urlparse(url).netloc
    return host.removeprefix("www.")


_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    # LLM output and web content end up in these pages, so always escape
    autoescape=select_autoescape(default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters["domain"] = domain


def render(template: str, **context) -> str:
    return _env.get_template(template).render(**context)
