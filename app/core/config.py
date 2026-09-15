import os
from pydantic_settings import BaseSettings
from pydantic import field_validator

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
    YOUTUBE_API_KEY: str = ""

    # ⚠️ فارغ افتراضيًا — يُملأ من متغيرات البيئة فقط.
    #
    # في Render → Environment → YOUTUBE_TRACKED_QUERIES:
    #   الصيغة الموصى بها (CSV):
    #     ai agents,ai voice cloning,local ai models,ai automation
    #
    #   الصيغة البديلة (JSON):
    #     ["ai agents","ai voice cloning","local ai models"]
    #
    # لو بقي فارغًا، الـcollector لن يجمع شيئًا.
    YOUTUBE_TRACKED_QUERIES: list[str] = []

    YOUTUBE_MAX_RESULTS_PER_QUERY: int = 25
    YOUTUBE_COLLECT_INTERVAL_MINUTES: int = 30
    YOUTUBE_SNAPSHOT_REFRESH_LIMIT: int = 100

    # ══════════════════════════════════════════════════════════════════
    # LLM Provider (لاحقًا)
    # ══════════════════════════════════════════════════════════════════
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = ""

    # ──────────────────────────────────────────────────────────────────
    # Validators — دعم CSV و JSON معًا
    # ──────────────────────────────────────────────────────────────────

    @field_validator("YOUTUBE_TRACKED_QUERIES", mode="before")
    @classmethod
    def _parse_queries(cls, v):
        """
        يقبل:
          - list[str] (من الكود)
          - JSON string: '["a","b","c"]'
          - CSV string:  'a,b,c'
          - فارغ / None → []
        """
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            v = v.strip()
            # جرّب JSON أولًا
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass
            # fallback إلى CSV
            return [x.strip() for x in v.split(",") if x.strip()]
        return []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if v is None or v == "":
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return ["*"]

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
