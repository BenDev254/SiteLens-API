from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os


class Settings(BaseSettings):
    # REQUIRED
    DATABASE_URL: str
    SECRET_KEY: str
    GEMINI_API_KEY: str

    # App
    APP_NAME: str = "sitelens-backend"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    MIGRATE_ON_START: bool = False

    # CORS
    CORS_ALLOW_ALL: bool = True
    CORS_ORIGINS: List[str] = []

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Google / Gemini
    GEMINI_MODEL: str = "gemini-3-pro-preview"
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_CX: Optional[str] = None

    # Email
    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: str

    class Config:
        case_sensitive = True
        env_file = ".env" if os.getenv("ENVIRONMENT") != "production" else None


settings = Settings()
