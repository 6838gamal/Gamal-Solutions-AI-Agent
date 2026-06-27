from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.v1.api import api_router
from app.api.public.router import router as public_router
from app.web.router import router as web_router
import os
from datetime import datetime

# ── Global server state (for /status page) ───────────────────────────────────
_SERVER_START = datetime.utcnow()
_keepalive_state: dict = {
    "url":        None,
    "last_ping":  None,
    "last_status": None,
    "ping_count": 0,
    "fail_count": 0,
    "history":    [],   # last 10 results
}


class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control: no-store to all protected HTML page responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(NoCacheHTMLMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files — relative to project root
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse, Response
    fav = os.path.join(os.path.dirname(__file__), "../static/favicon.ico")
    if os.path.exists(fav):
        return FileResponse(fav)
    return Response(status_code=204)


# Internal API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Public API routes (API-key authenticated)
app.include_router(public_router, prefix="/api/public/v1")

# Web (HTML) routes
app.include_router(web_router)


@app.on_event("startup")
def startup():
    import threading
    def init_db():
        try:
            Base.metadata.create_all(bind=engine)
            # Migrate new knowledge_documents columns (idempotent)
            from sqlalchemy import text
            migrations = [
                "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS file_path VARCHAR(500)",
                "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS file_name VARCHAR(255)",
                "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS file_size INTEGER DEFAULT 0",
                "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS is_trained BOOLEAN DEFAULT FALSE",
                "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS trained_at TIMESTAMP",
                # Telegram tables
                """CREATE TABLE IF NOT EXISTS telegram_accounts (
                    id SERIAL PRIMARY KEY,
                    api_id VARCHAR(50),
                    api_hash VARCHAR(100),
                    phone VARCHAR(30),
                    session_string TEXT,
                    phone_code_hash VARCHAR(200),
                    status VARCHAR(30) DEFAULT 'disconnected',
                    telegram_user_id VARCHAR(50),
                    telegram_username VARCHAR(100),
                    telegram_first_name VARCHAR(100),
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )""",
                """CREATE TABLE IF NOT EXISTS telegram_messages (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER REFERENCES telegram_accounts(id),
                    message_id INTEGER,
                    chat_id VARCHAR(50),
                    chat_title VARCHAR(255),
                    chat_type VARCHAR(30),
                    sender_id VARCHAR(50),
                    sender_name VARCHAR(255),
                    sender_username VARCHAR(100),
                    content TEXT,
                    media_type VARCHAR(30),
                    direction VARCHAR(10) DEFAULT 'incoming',
                    is_read BOOLEAN DEFAULT FALSE,
                    analysis_result JSONB DEFAULT '{}',
                    is_analyzed BOOLEAN DEFAULT FALSE,
                    reply_sent BOOLEAN DEFAULT FALSE,
                    replied_at TIMESTAMP,
                    received_at TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW()
                )""",
                """CREATE TABLE IF NOT EXISTS telegram_reply_rules (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER REFERENCES telegram_accounts(id),
                    rule_name VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    target_type VARCHAR(30) DEFAULT 'all',
                    target_chat_id VARCHAR(50),
                    target_sender_username VARCHAR(100),
                    keywords JSONB DEFAULT '[]',
                    reply_mode VARCHAR(30) DEFAULT 'manual',
                    agent_id INTEGER REFERENCES agents(id),
                    reply_template TEXT,
                    reply_delay_seconds INTEGER DEFAULT 0,
                    max_replies_per_hour INTEGER DEFAULT 10,
                    replies_sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )""",
                "ALTER TABLE telegram_accounts ADD COLUMN IF NOT EXISTS market_analysis JSONB",
                "ALTER TABLE telegram_accounts ADD COLUMN IF NOT EXISTS market_analysis_at TIMESTAMP",
                # API Keys table
                """CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    key_hash VARCHAR(128) UNIQUE NOT NULL,
                    key_prefix VARCHAR(12) NOT NULL,
                    permissions JSONB DEFAULT '[]',
                    is_active BOOLEAN DEFAULT TRUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_used_at TIMESTAMP,
                    expires_at TIMESTAMP
                )""",
            ]
            with engine.connect() as conn:
                for sql in migrations:
                    try:
                        conn.execute(text(sql))
                    except Exception:
                        pass
                conn.commit()
            db = SessionLocal()
            try:
                from app.domains.auth.service import ensure_superuser
                ensure_superuser(db)
                # Validate stored Telegram session on startup
                try:
                    from app.domains.telegram.service import validate_and_refresh_session
                    validate_and_refresh_session(db)
                except Exception as tg_err:
                    print(f"Telegram session check skipped: {tg_err}")
            finally:
                db.close()
        except Exception as e:
            print(f"DB init warning: {e}")
    threading.Thread(target=init_db, daemon=True).start()

    # ── Auto-sync Telegram messages every 60 seconds ──────────────────────
    import time
    def telegram_auto_sync():
        # Wait for DB to be ready first
        time.sleep(15)
        while True:
            try:
                from app.domains.telegram.models import TelegramAccount, TelegramConnectionStatus
                from app.domains.telegram.service import sync_messages, analyze_pending
                db = SessionLocal()
                try:
                    account = db.query(TelegramAccount).filter_by(
                        status=TelegramConnectionStatus.CONNECTED
                    ).first()
                    if account:
                        new_count = sync_messages(db, account)
                        if new_count > 0:
                            analyze_pending(db, account)
                            print(f"[AutoSync] استُقبلت {new_count} رسالة جديدة وتم تحليلها تلقائياً")
                except Exception as sync_err:
                    print(f"[AutoSync] خطأ: {sync_err}")
                finally:
                    db.close()
            except Exception as outer_err:
                print(f"[AutoSync] خطأ خارجي: {outer_err}")
            time.sleep(60)

    threading.Thread(target=telegram_auto_sync, daemon=True).start()

    # ── Keep-Alive Ping (prevents Render / free-tier sleep) ───────────────
    def _detect_app_url() -> str:
        """Auto-detect the public app URL from common hosting platforms."""
        import os as _os
        import socket

        candidates = [
            _os.environ.get("RENDER_EXTERNAL_URL"),        # Render (auto)
            _os.environ.get("REPLIT_DEV_DOMAIN") and
                f"https://{_os.environ['REPLIT_DEV_DOMAIN']}",  # Replit (auto)
            _os.environ.get("RAILWAY_PUBLIC_DOMAIN") and
                f"https://{_os.environ['RAILWAY_PUBLIC_DOMAIN']}",  # Railway (auto)
            _os.environ.get("FLY_APP_NAME") and
                f"https://{_os.environ['FLY_APP_NAME']}.fly.dev",  # Fly.io (auto)
            _os.environ.get("APP_URL"),                    # manual override
        ]

        for url in candidates:
            if url:
                return url.rstrip("/")

        # Last resort: local
        return "http://localhost:5000"

    def keep_alive():
        """Ping own /health every 7 min so free-tier hosts never spin down."""
        import urllib.request

        time.sleep(20)
        url = _detect_app_url() + "/health"
        _keepalive_state["url"] = url
        print(f"[KeepAlive] جاهز — سيُرسَل ping كل 7 دقائق إلى: {url}")

        while True:
            now = datetime.utcnow()
            entry: dict = {"time": now.isoformat(), "ok": False, "status": None}
            try:
                with urllib.request.urlopen(url, timeout=15) as resp:
                    entry["ok"] = True
                    entry["status"] = resp.status
                    _keepalive_state["ping_count"] += 1
                    _keepalive_state["last_ping"] = now.isoformat()
                    _keepalive_state["last_status"] = resp.status
                    print(f"[KeepAlive] ✓ {resp.status} — {url}")
            except Exception as e:
                entry["error"] = str(e)
                _keepalive_state["fail_count"] += 1
                print(f"[KeepAlive] ✗ فشل الاتصال: {e}")
            hist = _keepalive_state["history"]
            hist.append(entry)
            if len(hist) > 10:
                hist.pop(0)
            time.sleep(7 * 60)

    threading.Thread(target=keep_alive, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.VERSION, "project": settings.PROJECT_NAME}


@app.get("/status")
def status_page(request: Request):
    """Public server status dashboard — no auth required."""
    from fastapi.responses import HTMLResponse
    from fastapi.templating import Jinja2Templates
    import platform

    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    tpl = Jinja2Templates(directory=templates_dir)

    now = datetime.utcnow()
    uptime_secs = int((now - _SERVER_START).total_seconds())
    hours, rem   = divmod(uptime_secs, 3600)
    minutes, sec = divmod(rem, 60)
    uptime_str   = f"{hours}س {minutes}د {sec}ث"

    # Quick DB check
    db_ok = False
    try:
        from app.core.database import engine as _engine
        from sqlalchemy import text as _text
        with _engine.connect() as conn:
            conn.execute(_text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    context = {
        "request":      request,
        "start_time":   _SERVER_START.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "uptime":       uptime_str,
        "uptime_secs":  uptime_secs,
        "python":       platform.python_version(),
        "platform_info": platform.system() + " " + platform.release(),
        "db_ok":        db_ok,
        "ka":           _keepalive_state,
        "version":      settings.VERSION,
        "project":      settings.PROJECT_NAME,
    }
    return tpl.TemplateResponse("status.html", context)
