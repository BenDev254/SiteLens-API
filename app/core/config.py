import os
from pydantic_settings import BaseSettings
from typing import List, Optional


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

    # CORS / Uploads

    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    CORS_ORIGINS: List[str] = ["https://2ljwk848107dqcj56wagzi5tjhvk3dj7jyaqih9sas9okpqj6m-h852644758.scf.usercontent.goog"]
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Google / Gemini
    GEMINI_MODEL: str = "gemini-3-pro-preview"
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_CX: Optional[str] = None

    class Config:
        case_sensitive = True
        # Load .env ONLY when not production
        env_file = ".env" if os.getenv("ENVIRONMENT") != "production" else None


settings = Settings()
