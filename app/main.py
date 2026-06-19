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
