from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.v1.api import api_router
from app.web.router import router as web_router
import os


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


# API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

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
            finally:
                db.close()
        except Exception as e:
            print(f"DB init warning: {e}")
    threading.Thread(target=init_db, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.VERSION, "project": settings.PROJECT_NAME}
