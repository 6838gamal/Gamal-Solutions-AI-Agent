from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from app.core.database import get_db
from app.domains.youtube.services import videos as videos_svc

router = APIRouter(prefix="/youtube", tags=["youtube-web"])

_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "templates",
)
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


@router.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    return templates.TemplateResponse("youtube/search.html", {
        "request": request,
        "page": "youtube",
    })


@router.get("/video/{video_id}", response_class=HTMLResponse)
def video_page(request: Request, video_id: int, db: Session = Depends(get_db)):
    v = videos_svc.get_video(db, video_id)
    if not v:
        return templates.TemplateResponse("youtube/not_found.html", {
            "request": request, "page": "youtube",
        }, status_code=404)
    snaps = videos_svc.get_snapshots(db, video_id)
    velocity = videos_svc.compute_velocity(db, video_id)
    return templates.TemplateResponse("youtube/video.html", {
        "request": request,
        "page": "youtube",
        "video": v,
        "snapshots": snaps,
        "velocity": velocity,
    })
