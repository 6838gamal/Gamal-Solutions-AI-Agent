import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gamal Solutions AI Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DB_URL: str = ""
    SECRET_KEY: str = "gamal-solutions-enterprise-secret-key-2024-super-secure-jwt"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    BACKEND_PORT: int = 5000
    ENVIRONMENT: str = "production"

    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    def model_post_init(self, __context):
        # Prefer Replit's managed DATABASE_URL, fall back to DB_URL env var
        db_url = os.environ.get("DATABASE_URL", "") or self.DB_URL
        if db_url:
            object.__setattr__(self, "DB_URL", db_url)

        secret = os.environ.get("SESSION_SECRET", "") or self.SECRET_KEY
        if secret:
            object.__setattr__(self, "SECRET_KEY", secret)

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
