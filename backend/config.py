import os
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT_DIR / "outputs"

DEFAULT_MODEL = "openai:gpt-5.4-mini"


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
    allow_model_override: bool


@lru_cache
def get_settings() -> Settings:
    return Settings(
        llm_model=os.getenv("LLM_MODEL", DEFAULT_MODEL),
        llm_temperature=_env_float("LLM_TEMPERATURE"),
        max_revisions=int(os.getenv("MAX_REVISIONS", "2")),
        sources_per_article=int(os.getenv("SOURCES_PER_ARTICLE", "5")),
        news_time_range=os.getenv("NEWS_TIME_RANGE", "week") or None,
        allow_model_override=_env_bool("ALLOW_MODEL_OVERRIDE", True),
    )


def new_run_dir() -> str:
    return str(OUTPUTS_DIR / f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}")


@dataclass
class NewspaperContext:
    """Per-run configuration, available to every agent via LangGraph's runtime context."""

    model: str = field(default_factory=lambda: get_settings().llm_model)
    temperature: float | None = field(default_factory=lambda: get_settings().llm_temperature)
    max_revisions: int = field(default_factory=lambda: get_settings().max_revisions)
    sources_per_article: int = field(default_factory=lambda: get_settings().sources_per_article)
    news_time_range: str | None = field(default_factory=lambda: get_settings().news_time_range)
    output_dir: str = field(default_factory=new_run_dir)
