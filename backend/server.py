import json
import logging
import os
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StringConstraints, field_validator

from .agents import NoArticlesError
from .config import OUTPUTS_DIR, ROOT_DIR, NewspaperContext, get_settings
from .graph import stream_newspaper
from .llm import get_chat_model
from .state import Layout

logger = logging.getLogger("gpt_newspaper")

MAX_TOPICS = 6

Topic = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class NewspaperRequest(BaseModel):
    topics: list[Topic] = Field(min_length=1, max_length=MAX_TOPICS)
    layout: Layout = "layout_1"
    model: str | None = Field(default=None, description='Any LangChain model string, e.g. "anthropic:claude-sonnet-5-5"')

    @field_validator("layout", mode="before")
    @classmethod
    def strip_html_suffix(cls, value: str) -> str:
        # v1 clients sent "layout_1.html"
        return value.removesuffix(".html") if isinstance(value, str) else value


app = FastAPI(title="GPT Newspaper", version="2.0.0")


@app.get("/api/config")
def config() -> dict:
    settings = get_settings()
    return {
        "model": settings.llm_model,
        "allow_model_override": settings.allow_model_override,
        "max_topics": MAX_TOPICS,
    }


def build_context(request: NewspaperRequest) -> NewspaperContext:
    """Validate everything we can up front, so the user gets a clear error instead of a broken stream."""
    settings = get_settings()
    model = (request.model or "").strip() or settings.llm_model
    if model != settings.llm_model and not settings.allow_model_override:
        raise HTTPException(403, "Choosing a model per run is disabled on this server.")
    if not os.getenv("TAVILY_API_KEY"):
        raise HTTPException(400, "TAVILY_API_KEY is not set. Get a free key at https://tavily.com.")
    try:
        get_chat_model(model, settings.llm_temperature)
    except ImportError as e:
        raise HTTPException(400, f"Missing LangChain integration for “{model}”: {e}") from e
    except Exception as e:
        raise HTTPException(400, f"Could not load model “{model}”: {e}") from e
    return NewspaperContext(model=model)


@app.post("/api/newspaper")
async def create_newspaper(request: NewspaperRequest) -> StreamingResponse:
    """Stream newline-delimited JSON events while the newsroom works."""
    context = build_context(request)

    async def events():
        try:
            async for event in stream_newspaper(request.topics, request.layout, context):
                yield json.dumps(event) + "\n"
        except NoArticlesError as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        except Exception as e:
            logger.exception("Newspaper generation failed")
            yield json.dumps({"type": "error", "message": f"{type(e).__name__}: {e}"}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.post("/generate_newspaper")
async def generate_newspaper(request: NewspaperRequest) -> dict:
    """Blocking endpoint kept for v1 API compatibility."""
    context = build_context(request)
    try:
        async for event in stream_newspaper(request.topics, request.layout, context):
            if event["type"] == "done":
                return {"path": event["url"]}
    except NoArticlesError as e:
        raise HTTPException(422, str(e)) from e
    raise HTTPException(500, "Newspaper generation did not finish")


OUTPUTS_DIR.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")
app.mount("/", StaticFiles(directory=ROOT_DIR / "frontend", html=True), name="frontend")
