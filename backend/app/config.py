from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./studyos.db"
    redis_url: str = ""  # empty = in-memory cache
    jwt_secret: str
    jwt_expire_minutes: int = 60 * 24 * 30
    cors_origins: list[str] = ["http://localhost:3000"]

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-10-21"

    # Any OpenAI-compatible API: OpenAI, Groq, Gemini, OpenRouter, or local Ollama (http://localhost:11434/v1).
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"

    judge0_url: str = "http://localhost:2358"
    judge0_api_key: str = ""
    # Used when judge0_url is unreachable. Sends code to the free public Judge0 CE; set empty to disable.
    judge0_fallback_url: str = "https://ce.judge0.com"

    clist_username: str = ""
    clist_api_key: str = ""

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, v: str) -> str:
        # Hosted Postgres (Render, Neon) hands out postgres:// URLs; SQLAlchemy needs the psycopg driver name.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v


settings = Settings()
