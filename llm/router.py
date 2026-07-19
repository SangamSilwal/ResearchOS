import os
from langchain_core.language_models import BaseChatModel
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter
from core.config import settings


def sync_provider_env() -> None:
    """
    Push the current values of `settings` into os.environ.

    This used to run once at import time, which meant provider API keys
    were frozen the moment this module was first imported. The web UI
    lets a user save new keys after the process has already started, so
    this is now called from get_llm() on every invocation to make sure
    each newly-constructed LLM client picks up the latest keys.
    """
    os.environ["GROQ_API_KEY"] = settings.groq_api_key
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key
    os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key


# Keep the same behavior for existing callers (CLI/tests) that import this
# module and expect the environment to already be populated.
sync_provider_env()


def get_llm(model_key: str) -> BaseChatModel:
    """
    Format: "provider/model-name"
    """
    sync_provider_env()
    provider, model_name = model_key.split("/", 1)

    if provider == "groq":
        return ChatGroq(
            model=model_name,
            temperature=0.1,
            max_retries=3,
        )

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.1,
            max_retries=3,
        )

    if provider == "mistral":
        return ChatMistralAI(
            model=model_name,
            temperature=0.1,
            max_retries=3,
        )

    if provider == "openrouter":
        return ChatOpenRouter(
            model=model_name,
            temperature=0.1,
            max_retries=3
        )

    raise ValueError(
        f"Unknown provider '{provider}'. "
        f"Supported: groq, gemini, mistral. Got: '{model_key}'"
    )
