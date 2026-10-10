from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


@lru_cache(maxsize=16)
def get_chat_model(model: str, temperature: float | None = None) -> BaseChatModel:
    """Build any LangChain chat model from a "<provider>:<model>" string.

    Examples: "openai:gpt-5.4-mini", "anthropic:claude-sonnet-5-5",
    "google_genai:gemini-2.5-flash", "ollama:llama3.1".
    """
    kwargs = {"max_retries": 2}
    if temperature is not None:
        kwargs["temperature"] = temperature
    return init_chat_model(model, **kwargs)
