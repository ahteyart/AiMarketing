from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # Database — Railway/Neon provide postgres:// or postgresql://, normalize to asyncpg
    database_url: str = "postgresql+asyncpg://aimarketing:aimarketing@localhost:5432/aimarketing"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Canva (MCP session only — not used by Railway backend)
    canva_client_id: str = ""
    canva_client_secret: str = ""

    # Higgsfield — https://cloud.higgsfield.ai/api-keys
    hf_api_key: str = ""
    hf_secret: str = ""

    # Google Sheets + Drive
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/export/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
