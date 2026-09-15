from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import json

from app.core.database import get_db
from app.core.config import settings
from app.domains.youtube.services import videos as videos_svc

router = APIRouter(prefix="/youtube", tags=["youtube-web"])

# templates directory — نفس المجلد المستخدم في web/router.py
_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "templates",
)
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def youtube_page(request: Request, db: Session = Depends(get_db)):
    """
    صفحة YouTube الرئيسية — 4 تبويبات.
    تُمرَّر tracked_queries_json لتملأ تبويب "كلمات التتبع".
    """
    # اجلب قائمة الكلمات من الإعدادات
    tracked = getattr(settings, "YOUTUBE_TRACKED_QUERIES_RAW", []) or []
    tracked_json = json.dumps(tracked, ensure_ascii=False)

    # هل مفتاح YouTube مُعرَّف؟
    api_key_set = bool(getattr(settings, "YOUTUBE_API_KEY", ""))

    return templates.TemplateResponse("youtube.html", {
        "request": request,
        "page": "youtube",
        "tracked_queries_json": tracked_json,
        "tracked_queries_count": len(tracked),
        "api_key_set": api_key_set,
    })


@router.get("/video/{video_id}", response_class=HTMLResponse)
def youtube_video_page(request: Request, video_id: int, db: Session = Depends(get_db)):
    """صفحة تفاصيل الفيديو — لاحقًا."""
    v = videos_svc.get_video(db, video_id)
    if not v:
        return templates.TemplateResponse("youtube.html", {
            "request": request,
            "page": "youtube",
            "tracked_queries_json": "[]",
            "tracked_queries_count": 0,
            "api_key_set": bool(getattr(settings, "YOUTUBE_API_KEY", "")),
        }, status_code=404)
    snaps = videos_svc.get_snapshots(db, video_id)
    velocity = videos_svc.compute_velocity(db, video_id)
    return templates.TemplateResponse("youtube.html", {
        "request": request,
        "page": "youtube",
        "tracked_queries_json": "[]",
        "tracked_queries_count": 0,
        "api_key_set": bool(getattr(settings, "YOUTUBE_API_KEY", "")),
        "video": v,
        "snapshots": snaps,
        "velocity": velocity,
    })
