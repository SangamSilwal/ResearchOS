import os
from langchain_core.language_models import BaseChatModel
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings

os.environ["GROQ_API_KEY"] = settings.groq_api_key
os.environ["GOOGLE_API_KEY"] = settings.google_api_key
os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key

def get_llm(model_key: str) -> BaseChatModel:
    """
    Format: "provider/model-name"
    """
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
 
    raise ValueError(
        f"Unknown provider '{provider}'. "
        f"Supported: groq, gemini, mistral. Got: '{model_key}'"
    )
