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
    orchestrator_model: str = "mistral/mistral-small"
    researcher_model: str = "mistral/mistral-small"
    coder_model: str = "mistral/mistral-small"
    critic_model: str = "mistral/mistral-small"
    planner_model: str = "mistral/mistral-small"
    summarizer_model: str = "mistral/mistral-small"
    github_token: str = ""
    architect_model_a: str = "mistral/mistral-small"
    architect_model_b: str = "mistral/mistral-small"
    architect_judge_model: str = "mistral/mistral-small"
    output_dir: str = "./output"
    web_username: str = ""
    web_password_hash: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()