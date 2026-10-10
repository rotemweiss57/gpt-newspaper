"""Turn a request (from the web UI, the API or the CLI) into a validated run context."""

import os

from .config import LANGUAGES, NewspaperContext, get_settings
from .images import IMAGE_STYLES, PHOTOS
from .llm import PROVIDER_KEY_ENV, get_chat_model, has_server_key, infer_provider


class SetupError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def make_context(
    *,
    model: str | None = None,
    api_key: str | None = None,
    tavily_api_key: str | None = None,
    language: str = "en",
    images: str | None = None,
    image_api_key: str | None = None,
    allow_override: bool | None = None,
    **overrides,
) -> NewspaperContext:
    """Validate everything up front, so users get a clear error instead of a half-printed edition."""
    settings = get_settings()
    model = model or settings.llm_model
    allow_override = settings.allow_model_override if allow_override is None else allow_override
    if model != settings.llm_model and not allow_override:
        raise SetupError("Choosing a model per run is disabled on this server.", 403)
    if language not in LANGUAGES:
        raise SetupError(f"Unsupported language “{language}”. Choose one of: {', '.join(LANGUAGES)}")
    images = images or settings.image_style
    if images != PHOTOS and images not in IMAGE_STYLES:
        raise SetupError(f"Unsupported image style “{images}”. Choose one of: {', '.join([*IMAGE_STYLES, PHOTOS])}")

    if not tavily_api_key and not os.getenv("TAVILY_API_KEY"):
        raise SetupError(
            "Add your Tavily API key under “Model & API keys”, or set TAVILY_API_KEY (free at https://tavily.com)."
        )

    provider = infer_provider(model)
    if not api_key and provider in PROVIDER_KEY_ENV and not has_server_key(provider):
        raise SetupError(f"Add your {provider} API key under “Model & API keys”, or set {PROVIDER_KEY_ENV[provider]}.")

    try:
        get_chat_model(model, settings.llm_temperature, api_key)
    except ImportError as e:
        raise SetupError(f"Missing LangChain integration for “{model}”: {e}") from e
    except Exception as e:
        raise SetupError(f"Could not load model “{model}”: {e}") from e

    return NewspaperContext(
        model=model,
        api_key=api_key or None,
        tavily_api_key=tavily_api_key or None,
        image_api_key=image_api_key or None,
        image_style=None if images == PHOTOS else images,
        language_code=language,
        **overrides,
    )
