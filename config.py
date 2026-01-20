"""
Configuration settings for SiteLens AI Backend
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = ""

    DATABASE_URL: str = ""  

    SECRET_KEY: str = "dev-secret-key-change-in-production"

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]

    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg",
        "video/mp4",
        "video/quicktime"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
