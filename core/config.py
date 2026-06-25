from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    secret_key: str = "dev-secret-key"
    groq_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""
    openrouter_api_key: str = ""
    tavily_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "research-os"
    database_url: str = "sqlite+aiosqlite:///./research_os.db"
    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_dir: str = "./chroma_db"
    orchestrator_model: str = "groq/llama-3.3-70b-versatile"
    researcher_model: str = "groq/llama-3.3-70b-versatile"
    coder_model: str = "groq/qwen3-32b"
    critic_model: str = "mistral/devstral-small"
    reasoner_model: str = "openrouter/deepseek/deepseek-r1:free"
    github_token: str = ""
    architect_model_a: str = "mistral/mistral-small"
    architect_model_b: str = "groq/llama-3.3-70b-versatile"
    architect_judge_model: str = "groq/llama-3.3-70b-versatile"



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()