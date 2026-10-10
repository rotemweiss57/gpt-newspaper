import json
import os
from datetime import UTC, datetime

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from ..config import NewspaperContext, public_url
from ..state import NewspaperState
from .common import today
from .designer import asset_url

EDITION_FILE = "edition.json"


def publisher_node(state: NewspaperState, runtime: Runtime[NewspaperContext]) -> dict:
    ctx = runtime.context
    os.makedirs(ctx.output_dir, exist_ok=True)
    path = os.path.join(ctx.output_dir, "newspaper.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(state["newspaper_html"])

    # Metadata for the archive of past editions
    articles = sorted(state.get("articles", []), key=lambda a: a.get("index", 0))
    edition = {
        "id": os.path.basename(ctx.output_dir),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "date": today(),
        "title": articles[0]["title"] if articles else "",
        "topics": state.get("topics", []),
        "layout": state.get("layout"),
        "model": ctx.model,
        "language": ctx.language_code,
        "editors_note": state.get("editors_note", ""),
        "url": public_url(path),
        "articles": [
            {key: a.get(key) for key in ("query", "title", "summary", "url", "reading_minutes", "illustrated")}
            | {"image": asset_url(ctx.output_dir, a.get("image", ""))}
            for a in articles
        ],
    }
    with open(os.path.join(ctx.output_dir, EDITION_FILE), "w", encoding="utf-8") as f:
        json.dump(edition, f, ensure_ascii=False, indent=2)

    get_stream_writer()({"stage": "publish", "message": "Hot off the press"})
    return {"newspaper_path": path}
