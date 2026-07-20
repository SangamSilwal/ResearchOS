from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    secret_key: str = "dev-secret-key"

    # ---- platform-level provider keys -------------------------------
    # Used as the fallback whenever a run doesn't have a per-user BYO key
    # (see core/runtime.py). groq is the "free default" provider -- every
    # agent role works out of the box on the platform's own Groq key even
    # if a user never configures anything.
    groq_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""
    openrouter_api_key: str = ""
    tavily_api_key: str = ""
    github_token: str = ""

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "research-os"

    # ---- database (Postgres / Supabase) ------------------------------
    # Supabase: Project Settings -> Database -> Connection string ->
    # "URI" (choose the asyncpg-compatible transaction pooler on port
    # 6543 for serverless, or the direct 5432 connection otherwise), then
    # swap the "postgresql://" prefix for "postgresql+asyncpg://".
    database_url: str = "postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
    sql_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_dir: str = "./chroma_db"

    # ---- per-agent default models -------------------------------------
    # Used whenever a user hasn't set a custom model for that agent role
    # (see web/model_defaults.py + core/runtime.py). All default to Groq
    # so a brand new, unconfigured account can still run goals immediately.
    orchestrator_model: str = "groq/llama-3.3-70b-versatile"
    researcher_model: str = "groq/llama-3.3-70b-versatile"
    coder_model: str = "groq/llama-3.3-70b-versatile"
    critic_model: str = "groq/llama-3.1-8b-instant"
    planner_model: str = "groq/llama-3.3-70b-versatile"
    summarizer_model: str = "groq/llama-3.1-8b-instant"
    architect_model_a: str = "groq/llama-3.3-70b-versatile"
    architect_model_b: str = "groq/llama-3.3-70b-versatile"
    architect_judge_model: str = "groq/llama-3.3-70b-versatile"

    output_dir: str = "./output"
    downloads_dir: str = "./downloads"

    # ---- auth -----------------------------------------------------------
    # OAuth apps: Google Cloud Console / GitHub Developer Settings.
    # Callback URLs to register there:
    #   {OAUTH_REDIRECT_BASE_URL}/auth/google/callback
    #   {OAUTH_REDIRECT_BASE_URL}/auth/github/callback
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:8080"
    # Where to send the browser after a successful OAuth login, with the
    # issued JWT as a query param (?token=...). Leave blank while there's
    # no frontend yet -- the callback then returns the token as JSON
    # instead, which is convenient for testing straight from a browser.
    frontend_url: str = ""
    jwt_expire_minutes: int = 60 * 24 * 7

    # legacy fields from the single-operator HTML prototype -- unused now
    # that auth is per-user OAuth+JWT, kept only so old .env files don't
    # fail validation.
    web_username: str = ""
    web_password_hash: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
