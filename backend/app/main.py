from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.v1.api import api_router
from app.web.router import router as web_router
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "../../static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
