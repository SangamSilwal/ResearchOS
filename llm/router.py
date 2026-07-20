from langchain_core.language_models import BaseChatModel
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter
from core.config import settings


def get_llm(model_key: str, api_key: str | None = None) -> BaseChatModel:
    """
    Format: "provider/model-name"

    api_key: an explicit per-call key (e.g. a decrypted BYO key resolved
    for the current user/run via core.runtime.resolve_model()). When
    omitted, falls back to the platform's own key for that provider from
    core.config.settings -- this is what run.py (the CLI) always does.

    The key is always passed as a constructor argument, never through
    os.environ: several requests for different users can be in flight on
    the same process at once, and mutating a process-global env var to
    pick a key for one of them would leak into the others.
    """
    provider, model_name = model_key.split("/", 1)

    if provider == "groq":
        return ChatGroq(
            model=model_name,
            temperature=0.1,
            max_retries=3,
            api_key=api_key or settings.groq_api_key,
        )

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.1,
            max_retries=3,
            google_api_key=api_key or settings.google_api_key,
        )

    if provider == "mistral":
        return ChatMistralAI(
            model=model_name,
            temperature=0.1,
            max_retries=3,
            api_key=api_key or settings.mistral_api_key,
        )

    if provider == "openrouter":
        return ChatOpenRouter(
            model=model_name,
            temperature=0.1,
            max_retries=3,
            api_key=api_key or settings.openrouter_api_key,
        )

    raise ValueError(
        f"Unknown provider '{provider}'. "
        f"Supported: groq, gemini, mistral, openrouter. Got: '{model_key}'"
    )
