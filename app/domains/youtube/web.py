# app/domains/youtube/web.py
"""
YouTube Web Pages
─────────────────
كل صفحات HTML الخاصة بـ YouTube:
  GET /youtube                     → الصفحة الرئيسية (4 تبويبات)
  GET /youtube/video/{video_id}    → تفاصيل الفيديو + snapshots + velocity
  GET /youtube/opportunities       → الفرص المكتشفة

ملاحظة: endpoints الـ JSON موجودة في app/domains/youtube/api.py
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import json
import jwt
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.templates import templates
from app.domains.auth import models as auth_models
from app.domains.youtube.services import videos as videos_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/youtube", tags=["youtube-web"])

COOKIE_NAME = "access_token"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _current_user(request: Request, db: Session):
    """يقرأ المستخدم من cookie الـ JWT. يُرجع None إذا غير مسجَّل."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        uid = payload.get("sub")
        if not uid:
            return None
        return (
            db.query(auth_models.User)
              .filter(auth_models.User.id == int(uid), auth_models.User.is_active.is_(True))
              .first()
        )
    except Exception:
        return None


def _safe_json(obj) -> str:
    """JSON آمن للحقن في <script> — يمنع كسر الصفحة عبر </script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _base_context(request: Request, user) -> dict:
    """سياق مشترك لكل صفحات YouTube."""
    tracked = list(getattr(settings, "YOUTUBE_TRACKED_QUERIES", []) or [])
    return {
        "request": request,
        "user": user,
        "page": "youtube",
        "tracked_queries_json": _safe_json(tracked),
        "tracked_queries_count": len(tracked),
        "api_key_set": bool(getattr(settings, "YOUTUBE_API_KEY", "")),
    }


def _require_user(request: Request, db: Session):
    """
    يُرجع (user, redirect_response).
    إذا user=None → استخدم redirect_response.
    """
    user = _current_user(request, db)
    if not user:
        return None, RedirectResponse(url="/login", status_code=302)
    return user, None


# ══════════════════════════════════════════════════════════════════════════════
# Pages
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse, include_in_schema=False)
def youtube_page(request: Request, db: Session = Depends(get_db)):
    """
    الصفحة الرئيسية لـ YouTube — 4 تبويبات:
      - البحث والاستكشاف
      - الفيديوهات المتتبَّعة
      - الأكثر صعودًا
      - كلمات التتبع
    """
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "youtube.html",
        _base_context(request, user),
    )


@router.get("/video/{video_id}", response_class=HTMLResponse)
def youtube_video_page(
    request: Request,
    video_id: int,
    db: Session = Depends(get_db),
):
    """
    تفاصيل الفيديو + snapshots + velocity.
    إذا لم يوجد الفيديو → نعرض صفحة YouTube الرئيسية مع 404.
    """
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    v = None
    try:
        v = videos_svc.get_video(db, video_id)
    except Exception as e:
        logger.exception("Failed to load video %s: %s", video_id, e)

    if not v:
        return templates.TemplateResponse(
            "youtube.html",
            _base_context(request, user),
            status_code=404,
        )

    # جمع snapshots + velocity بأمان
    snaps = []
    velocity = None
    try:
        snaps = videos_svc.get_snapshots(db, video_id) or []
    except Exception as e:
        logger.exception("Failed to load snapshots for %s: %s", video_id, e)

    try:
        velocity = videos_svc.compute_velocity(db, video_id)
    except Exception as e:
        logger.exception("Failed to compute velocity for %s: %s", video_id, e)

    ctx = _base_context(request, user)
    ctx.update({
        "video": v,
        "snapshots": snaps,
        "velocity": velocity,
        "active_tab": "video-detail",
    })

    # استخدم قالب منفصل إذا موجود، وإلا عد للقالب الرئيسي
    template_name = "youtube_video.html"
    try:
        return templates.TemplateResponse(template_name, ctx)
    except Exception:
        # fallback: نفس القالب الرئيسي
        return templates.TemplateResponse("youtube.html", ctx)


@router.get("/opportunities", response_class=HTMLResponse)
def youtube_opportunities_page(request: Request, db: Session = Depends(get_db)):
    """صفحة الفرص المكتشفة (Opportunities)."""
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect

    ctx = _base_context(request, user)
    ctx["page"] = "youtube-opportunities"
    return templates.TemplateResponse("youtube_opportunities.html", ctx)
