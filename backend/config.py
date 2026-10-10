import os
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT_DIR / "outputs"

# Only this project's .env, never one picked up from a parent directory
load_dotenv(ROOT_DIR / ".env")

DEFAULT_MODEL = "openai:gpt-5.4-mini"

# Languages an edition can be written in: code -> (name for the prompt, native name for the UI)
LANGUAGES: dict[str, tuple[str, str]] = {
    "en": ("English", "English"),
    "es": ("Spanish", "Español"),
    "fr": ("French", "Français"),
    "de": ("German", "Deutsch"),
    "it": ("Italian", "Italiano"),
    "pt": ("Portuguese", "Português"),
    "nl": ("Dutch", "Nederlands"),
    "pl": ("Polish", "Polski"),
    "tr": ("Turkish", "Türkçe"),
    "uk": ("Ukrainian", "Українська"),
    "ru": ("Russian", "Русский"),
    "he": ("Hebrew", "עברית"),
    "ar": ("Arabic", "العربية"),
    "hi": ("Hindi", "हिन्दी"),
    "ja": ("Japanese", "日本語"),
    "ko": ("Korean", "한국어"),
    "zh": ("Simplified Chinese", "简体中文"),
}
RTL_LANGUAGES = {"he", "ar"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str) -> float | None:
    value = os.getenv(name)
    return float(value) if value else None


@dataclass(frozen=True)
class Settings:
    llm_model: str
    # None means "use the provider's default". Some models (e.g. OpenAI reasoning
    # models) reject a custom temperature, so we only send one when asked to.
    llm_temperature: float | None
    max_revisions: int
    sources_per_article: int
    news_time_range: str | None
    searches_per_topic: int
    allow_model_override: bool
    max_concurrent_editions: int
    image_model: str
    image_style: str
    image_quality: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        llm_model=os.getenv("LLM_MODEL", DEFAULT_MODEL),
        llm_temperature=_env_float("LLM_TEMPERATURE"),
        max_revisions=int(os.getenv("MAX_REVISIONS", "2")),
        sources_per_article=int(os.getenv("SOURCES_PER_ARTICLE", "5")),
        news_time_range=os.getenv("NEWS_TIME_RANGE", "week") or None,
        searches_per_topic=int(os.getenv("SEARCHES_PER_TOPIC", "2")),
        allow_model_override=_env_bool("ALLOW_MODEL_OVERRIDE", True),
        max_concurrent_editions=int(os.getenv("MAX_CONCURRENT_EDITIONS", "4")),
        image_model=os.getenv("IMAGE_MODEL", "openai:gpt-image-2"),
        image_style=os.getenv("IMAGE_STYLE", "ink"),
        image_quality=os.getenv("IMAGE_QUALITY", "medium"),
    )


def new_run_dir() -> str:
    return str(OUTPUTS_DIR / f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}")


def public_url(path: str | Path) -> str:
    """URL the server exposes a generated file at."""
    return "/outputs/" + Path(path).resolve().relative_to(OUTPUTS_DIR.resolve()).as_posix()


@dataclass
class NewspaperContext:
    """Per-run configuration, available to every agent via LangGraph's runtime context."""

    model: str = field(default_factory=lambda: get_settings().llm_model)
    temperature: float | None = field(default_factory=lambda: get_settings().llm_temperature)
    max_revisions: int = field(default_factory=lambda: get_settings().max_revisions)
    sources_per_article: int = field(default_factory=lambda: get_settings().sources_per_article)
    news_time_range: str | None = field(default_factory=lambda: get_settings().news_time_range)
    searches_per_topic: int = field(default_factory=lambda: get_settings().searches_per_topic)
    language_code: str = "en"
    # None means "use the source's news photo"
    image_style: str | None = None
    image_model: str = field(default_factory=lambda: get_settings().image_model)
    image_quality: str = field(default_factory=lambda: get_settings().image_quality)
    output_dir: str = field(default_factory=new_run_dir)
    # Keys supplied by the user for this run only; they override the server's env vars
    api_key: str | None = field(default=None, repr=False)
    tavily_api_key: str | None = field(default=None, repr=False)
    image_api_key: str | None = field(default=None, repr=False)

    @property
    def language(self) -> str:
        return LANGUAGES[self.language_code][0]

    @property
    def page(self) -> dict:
        """What templates need to know about the edition's language."""
        return {"lang": self.language_code, "dir": "rtl" if self.language_code in RTL_LANGUAGES else "ltr"}
