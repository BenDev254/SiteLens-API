from pydantic_settings import BaseSettings
from typing import List
import json
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_NAME: str = "sitelens-backend"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    MIGRATE_ON_START: bool = False

    # CORS / Uploads
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Auth
    SECRET_KEY: str = "AIzaSyCwLSemyDNRjoXEtQpVb1_DnooE12iTvkw"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Google / Gemini
    GEMINI_API_KEY: str = "AIzaSyCwLSemyDNRjoXEtQpVb1_DnooE12iTvkw"
    GEMINI_MODEL: str = "gemini-3-pro-preview"
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_CX: Optional[str] = None
    

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
