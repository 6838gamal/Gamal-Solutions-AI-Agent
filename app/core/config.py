import os
import json
from pydantic_settings import BaseSettings

_DB_URL_DEFAULT = "postgresql://gamalalmaqtary:xndaLTpmEnsMY5cyBwXyX5sRRup8ooAD@dpg-dak2e10jo6nc73b85au0-a.oregon-postgres.render.com/gamal_solutions_ai_agent_db_h3bk"
_SECRET_KEY_DEFAULT = "gamal-solutions-enterprise-secret-key-2024-super-secure-jwt"


def _parse_csv_or_json_list(raw: str) -> list[str]:
    """
    يحوّل string إلى list[str].
    يدعم:
      - JSON:  '["a","b","c"]'
      - CSV:   'a,b,c'
      - فارغ → []
    """
    raw = (raw or "").strip()
    if not raw:
        return []
    # JSON أولًا
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    # fallback CSV
    return [x.strip() for x in raw.split(",") if x.strip()]


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

    # ⚠️ string خام — نستخدم property للتحويل
    BACKEND_CORS_ORIGINS: str = "*"

    # ══════════════════════════════════════════════════════════════════
    # YouTube Integration
    # ══════════════════════════════════════════════════════════════════
    YOUTUBE_API_KEY: str = ""

    # ⚠️ string خام — يُقرأ من البيئة بصيغة CSV أو JSON
    #
    # في Render → Environment:
    #   YOUTUBE_TRACKED_QUERIES_RAW = ai agents,ai voice cloning,local ai models
    #
    # أو JSON:
    #   YOUTUBE_TRACKED_QUERIES_RAW = ["ai agents","ai voice cloning"]
    YOUTUBE_TRACKED_QUERIES_RAW: str = ""

    YOUTUBE_MAX_RESULTS_PER_QUERY: int = 25
    YOUTUBE_COLLECT_INTERVAL_MINUTES: int = 30
    YOUTUBE_SNAPSHOT_REFRESH_LIMIT: int = 100

    # ══════════════════════════════════════════════════════════════════
    # LLM Provider (لاحقًا)
    # ══════════════════════════════════════════════════════════════════
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = ""

    # ══════════════════════════════════════════════════════════════════
    # Properties — تُقرأ من الكود كما لو كانت حقولًا عادية
    # ══════════════════════════════════════════════════════════════════

    @property
    def YOUTUBE_TRACKED_QUERIES(self) -> list[str]:
        """
        يحوّل YOUTUBE_TRACKED_QUERIES_RAW (string) إلى list[str].
        يدعم CSV و JSON.
        """
        return _parse_csv_or_json_list(self.YOUTUBE_TRACKED_QUERIES_RAW)

    @property
    def BACKEND_CORS_ORIGINS_LIST(self) -> list[str]:
        """
        يحوّل BACKEND_CORS_ORIGINS (string) إلى list[str].
        استخدم هذا في main.py بدلًا من BACKEND_CORS_ORIGINS.
        """
        raw = (self.BACKEND_CORS_ORIGINS or "").strip()
        if not raw:
            return ["*"]
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        return [x.strip() for x in raw.split(",") if x.strip()]

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
