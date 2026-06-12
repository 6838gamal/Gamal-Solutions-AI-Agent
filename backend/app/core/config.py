import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gamal Solutions AI Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DB_URL: str = os.getenv("DB_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    class Config:
        case_sensitive = True


settings = Settings()
