import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NFPL Access Control Service"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nfpl-super-secret-jwt-key-2026-production-ready")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Defaults to local SQLite file dev.db if no PostgreSQL URL is passed in env
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    POLICY_VERSION: str = "2026.1"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
