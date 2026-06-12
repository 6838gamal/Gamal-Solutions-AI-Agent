from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.v1.api import api_router

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

app.include_router(api_router, prefix=settings.API_V1_STR)


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
