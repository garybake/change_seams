"""
Seam 1 — Provider Abstraction.

Swap the LLM provider by changing LLM_PROVIDER in .env.
Supported values: openai | anthropic
"""
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings


def get_llm() -> BaseChatModel:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key or None,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {provider!r}. Supported: openai, anthropic"
        )
