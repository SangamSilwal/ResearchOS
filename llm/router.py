import os
from langchain_core.language_models import BaseChatModel
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter
from core.config import settings

os.environ["GROQ_API_KEY"] = settings.groq_api_key
os.environ["GOOGLE_API_KEY"] = settings.google_api_key
os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key


def _resolve_api_key(provider: str, override: str | None) -> str | None:
    if override:
        return override
    env_map = {
        "groq": "GROQ_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "llama": "GROQ_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var:
        return os.environ.get(env_var) or getattr(settings, env_var.lower(), None)
    return None


def get_llm(model_key: str, api_key: str | None = None) -> BaseChatModel:
    """
    Format: "provider/model-name"
    Optional api_key overrides the provider default (used for per-user BYO keys).
    """
    provider, model_name = model_key.split("/", 1)
    key = _resolve_api_key(provider, api_key)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required for anthropic models.")
        return ChatAnthropic(
            model=model_name,
            api_key=key,
            temperature=0.1,
            max_retries=3,
        )

    if provider == "groq" or provider == "llama":
        if not key:
            raise ValueError("GROQ_API_KEY is required for llama/groq models.")
        return ChatGroq(
            model=model_name,
            api_key=key,
            temperature=0.1,
            max_retries=3,
        )

    if provider == "gemini":
        if not key:
            raise ValueError("GOOGLE_API_KEY is required for gemini models.")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=key,
            temperature=0.1,
            max_retries=3,
        )

    if provider == "mistral":
        if not key:
            raise ValueError("MISTRAL_API_KEY is required for mistral models.")
        return ChatMistralAI(
            model=model_name,
            api_key=key,
            temperature=0.1,
            max_retries=3,
        )

    if provider == "openrouter":
        if not key:
            raise ValueError("OPENROUTER_API_KEY is required for openrouter models.")
        return ChatOpenRouter(
            model=model_name,
            openrouter_api_key=key,
            temperature=0.1,
            max_retries=3,
        )

    raise ValueError(
        f"Unknown provider '{provider}'. "
        f"Supported: anthropic, groq, llama, gemini, mistral, openrouter. Got: '{model_key}'"
    )
