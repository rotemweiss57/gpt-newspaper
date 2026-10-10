import os
from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

# Env var each provider reads its key from. None means no key is needed.
PROVIDER_KEY_ENV: dict[str, str | None] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_genai": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistralai": "MISTRAL_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "together": "TOGETHER_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "ollama": None,
}

_NAME_PREFIXES = {
    "gpt-": "openai", "o1": "openai", "o3": "openai", "o4": "openai",
    "claude": "anthropic", "gemini": "google_genai", "mistral": "mistralai", "grok": "xai",
}


def infer_provider(model: str) -> str | None:
    if ":" in model:
        return model.split(":", 1)[0]
    return next((p for prefix, p in _NAME_PREFIXES.items() if model.lower().startswith(prefix)), None)


def has_server_key(provider: str | None) -> bool:
    env = PROVIDER_KEY_ENV.get(provider or "", "")
    return env is None or bool(env and os.getenv(env))


@lru_cache(maxsize=16)
def get_chat_model(model: str, temperature: float | None = None, api_key: str | None = None) -> BaseChatModel:
    """Build any LangChain chat model from a "<provider>:<model>" string.

    Examples: "openai:gpt-5.4-mini", "anthropic:claude-sonnet-5-5",
    "google_genai:gemini-2.5-flash", "ollama:llama3.1".
    `api_key` overrides the provider's env var for this model only.
    """
    kwargs = {"max_retries": 2}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if api_key:
        kwargs["api_key"] = api_key
    return init_chat_model(model, **kwargs)
