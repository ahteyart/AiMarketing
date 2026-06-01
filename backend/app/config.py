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

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Storage (MinIO)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "aimarketing-media"
    minio_use_ssl: bool = False

    # AI
    anthropic_api_key: str = ""
    runway_api_key: str = ""
    video_generation_monthly_budget_usd: float = 200.0

    # Meta (Facebook + Instagram)
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_page_access_token: str = ""
    meta_instagram_business_account_id: str = ""

    # TikTok / Apify
    apify_api_token: str = ""

    # Xiaohongshu
    xhs_cookie_1: str = ""
    xhs_cookie_2: str = ""
    xhs_cookie_3: str = ""
    xhs_proxy_url: str = ""

    # Google Sheets
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/export/google-sheets/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
