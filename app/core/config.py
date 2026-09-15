import os
from pydantic_settings import BaseSettings

_DB_URL_DEFAULT = "postgresql://gamalalmaqtary:xndaLTpmEnsMY5cyBwXyX5sRRup8ooAD@dpg-dak2e10jo6nc73b85au0-a.oregon-postgres.render.com/gamal_solutions_ai_agent_db_h3bk"
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

    # ══════════════════════════════════════════════════════════════════
    # YouTube Integration
    # ══════════════════════════════════════════════════════════════════
    # مفتاح YouTube Data API v3 — احصل عليه من Google Cloud Console
    # https://console.cloud.google.com/apis/credentials
    YOUTUBE_API_KEY: str = ""

    # كلمات التتبع التلقائي — يعمل الـcollector عليها كل 30 دقيقة
    YOUTUBE_TRACKED_QUERIES: list[str] = [
        "ai agents",
        "ai voice cloning",
        "local ai models",
    ]

    # الحد الأقصى للنتائج لكل query (YouTube يسمح حتى 50)
    YOUTUBE_MAX_RESULTS_PER_QUERY: int = 25

    # الفاصل الزمني بين دورات الجمع (بالدقائق)
    YOUTUBE_COLLECT_INTERVAL_MINUTES: int = 30

    # عدد الفيديوهات الحديثة التي تُحدَّث snapshots لها في كل دورة
    YOUTUBE_SNAPSHOT_REFRESH_LIMIT: int = 100

    # ══════════════════════════════════════════════════════════════════
    # LLM Provider (لاحقًا — عند بناء Ideas Generator)
    # ══════════════════════════════════════════════════════════════════
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = ""

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
