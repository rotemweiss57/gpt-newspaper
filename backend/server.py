import json
import logging
import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StringConstraints, field_validator

from . import __version__
from .agents import EDITION_FILE, NoArticlesError
from .config import LANGUAGES, OUTPUTS_DIR, ROOT_DIR, NewspaperContext, get_settings
from .graph import stream_newspaper
from .images import IMAGE_STYLES, PHOTOS
from .llm import PROVIDER_KEY_ENV, has_server_key
from .setup import SetupError, make_context
from .state import Layout

logger = logging.getLogger("gpt_newspaper")

MAX_TOPICS = 6
MAX_EDITIONS_LISTED = 12

Topic = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ApiKey = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
ModelName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200, pattern=r"^[\w.:/@\-]*$")]


class NewspaperRequest(BaseModel):
    topics: list[Topic] = Field(min_length=1, max_length=MAX_TOPICS)
    layout: Layout = "layout_1"
    language: str = "en"
    model: ModelName | None = Field(
        default=None, description='Any LangChain model string, e.g. "anthropic:claude-sonnet-5-5"'
    )
    # Optional bring-your-own keys. Used for this run only, never stored or logged.
    api_key: ApiKey | None = Field(default=None, description="API key for the model's provider")
    tavily_api_key: ApiKey | None = None
    images: str | None = Field(
        default=None, description='Illustration style ("ink", "engraving", "risograph") or "photos"'
    )
    image_api_key: ApiKey | None = Field(default=None, description="Key for the image provider, if different")

    @field_validator("layout", mode="before")
    @classmethod
    def strip_html_suffix(cls, value: str) -> str:
        # v1 clients sent "layout_1.html"
        return value.removesuffix(".html") if isinstance(value, str) else value

    @field_validator("language")
    @classmethod
    def known_language(cls, value: str) -> str:
        if value not in LANGUAGES:
            raise ValueError(f"Unsupported language. Choose one of: {', '.join(LANGUAGES)}")
        return value


app = FastAPI(title="GPT Newspaper", version=__version__)

# --- Security ---------------------------------------------------------------

_FONTS = "https://fonts.googleapis.com"
_CSP_COMMON = (
    "default-src 'self'; img-src 'self' https: data:; "
    f"style-src 'self' 'unsafe-inline' {_FONTS}; font-src https://fonts.gstatic.com; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
# The app itself runs no inline script. Generated pages only use tiny inline handlers
# (image fallbacks, print button); all model output in them is escaped by Jinja.
CSP_APP = f"{_CSP_COMMON}; script-src 'self'"
CSP_GENERATED = f"{_CSP_COMMON}; script-src 'unsafe-inline'"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    headers = response.headers
    headers.setdefault(
        "Content-Security-Policy", CSP_GENERATED if request.url.path.startswith("/outputs/") else CSP_APP
    )
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # Always revalidate (cheap 304s via ETag), so upgrades never mix new HTML with stale JS
    headers.setdefault("Cache-Control", "no-cache")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI echoes the offending input by default; that input might be someone's API key
    errors = [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


class EditionSlots:
    """Caps how many editions run at once, so one server can't be flooded (or run up a huge bill)."""

    def __init__(self) -> None:
        self.active = 0

    def acquire(self) -> None:
        if self.active >= get_settings().max_concurrent_editions:
            raise HTTPException(429, "The newsroom is busy printing other editions. Try again in a minute.")
        self.active += 1

    def release(self) -> None:
        self.active -= 1


slots = EditionSlots()

# --- API --------------------------------------------------------------------


@app.get("/api/config")
def config() -> dict:
    settings = get_settings()
    return {
        "version": __version__,
        "model": settings.llm_model,
        "allow_model_override": settings.allow_model_override,
        "max_topics": MAX_TOPICS,
        "languages": {code: native for code, (_, native) in LANGUAGES.items()},
        "images": {
            "default": settings.image_style,
            "model": settings.image_model,
            "styles": {style: label for style, (label, _) in IMAGE_STYLES.items()} | {PHOTOS: "News photos"},
        },
        # Only whether a key is configured, never the key itself
        "server_keys": {
            "tavily": bool(os.getenv("TAVILY_API_KEY")),
            **{provider: has_server_key(provider) for provider in PROVIDER_KEY_ENV},
        },
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/editions")
def editions() -> list[dict]:
    """The most recent editions printed on this server, newest first."""
    found = []
    for path in OUTPUTS_DIR.glob(f"*/{EDITION_FILE}"):
        try:
            found.append((path.stat().st_mtime, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    found.sort(key=lambda item: item[0], reverse=True)
    return [
        {key: edition.get(key) for key in ("id", "created_at", "date", "title", "topics", "model", "language", "url")}
        | {"image": next((a.get("image") for a in edition.get("articles", []) if a.get("image")), "")}
        for _, edition in found[:MAX_EDITIONS_LISTED]
    ]


def build_context(request: NewspaperRequest) -> NewspaperContext:
    try:
        return make_context(
            model=request.model,
            api_key=request.api_key,
            tavily_api_key=request.tavily_api_key,
            language=request.language,
            images=request.images,
            image_api_key=request.image_api_key,
        )
    except SetupError as e:
        raise HTTPException(e.status, str(e)) from e


@app.post("/api/newspaper")
async def create_newspaper(request: NewspaperRequest) -> StreamingResponse:
    """Stream newline-delimited JSON events while the newsroom works."""
    context = build_context(request)
    slots.acquire()

    async def events():
        try:
            async for event in stream_newspaper(request.topics, request.layout, context):
                yield json.dumps(event) + "\n"
        except NoArticlesError as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        except Exception as e:
            logger.exception("Newspaper generation failed")
            yield json.dumps({"type": "error", "message": f"{type(e).__name__}: {e}"}) + "\n"
        finally:
            slots.release()

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})


@app.post("/generate_newspaper")
async def generate_newspaper(request: NewspaperRequest) -> dict:
    """Blocking endpoint kept for v1 API compatibility."""
    context = build_context(request)
    slots.acquire()
    try:
        async for event in stream_newspaper(request.topics, request.layout, context):
            if event["type"] == "done":
                return {"path": event["url"]}
    except NoArticlesError as e:
        raise HTTPException(422, str(e)) from e
    finally:
        slots.release()
    raise HTTPException(500, "Newspaper generation did not finish")


OUTPUTS_DIR.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")
app.mount("/", StaticFiles(directory=ROOT_DIR / "frontend", html=True), name="frontend")
