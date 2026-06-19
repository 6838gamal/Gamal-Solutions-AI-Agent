import os
from pydantic_settings import BaseSettings

_DB_URL_DEFAULT = "postgresql://gamalalmaqtary:Mxsof46L7GzfDvSI8vyAkt87zmLDzg6P@dpg-d8jrfmt7vvec73e1v6d0-a.virginia-postgres.render.com/gamal_solutions_ai_agent_db"
_SECRET_KEY_DEFAULT = "gamal-solutions-enterprise-secret-key-2024-super-secure-jwt"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gamal Solutions AI Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DB_URL: str = _DB_URL_DEFAULT
    SECRET_KEY: str = _SECRET_KEY_DEFAULT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    BACKEND_PORT: int = 5000
    ENVIRONMENT: str = "production"

    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    def model_post_init(self, __context):
        if not self.DB_URL or self.DB_URL.strip() == "":
            object.__setattr__(self, "DB_URL", _DB_URL_DEFAULT)
        if not self.SECRET_KEY or self.SECRET_KEY.strip() == "":
            object.__setattr__(self, "SECRET_KEY", _SECRET_KEY_DEFAULT)

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
