import os

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from ..config import NewspaperContext
from ..state import NewspaperState


def publisher_node(state: NewspaperState, runtime: Runtime[NewspaperContext]) -> dict:
    output_dir = runtime.context.output_dir
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "newspaper.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(state["newspaper_html"])

    get_stream_writer()({"stage": "publish", "message": "Hot off the press"})
    return {"newspaper_path": path}
