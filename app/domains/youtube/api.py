from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.core.config import settings
from app.domains.youtube.services import videos as videos_svc
from app.domains.youtube.services import collector as collector_svc  # إن وُجد

router = APIRouter(prefix="/api/v1/youtube", tags=["youtube-api"])


# ─── Stats ────────────────────────────────────────────────────────────────
@router.get("/stats")
def youtube_stats(db: Session = Depends(get_db)):
    return {
        "videos":    videos_svc.count_videos(db),
        "channels":  videos_svc.count_channels(db),
        "snapshots": videos_svc.count_snapshots(db),
        "rising":    videos_svc.count_rising(db, min_velocity=100),
    }


# ─── Search ───────────────────────────────────────────────────────────────
@router.get("/search")
def youtube_search(
    q: str = Query(..., min_length=2),
    max_results: int = Query(25, ge=1, le=50),
    persist: bool = Query(True),
    db: Session = Depends(get_db),
):
    if not settings.YOUTUBE_API_KEY:
        raise HTTPException(400, "YOUTUBE_API_KEY غير مُعرَّف")
    results = videos_svc.search_youtube(
        db, query=q, max_results=max_results, persist=persist
    )
    return {"query": q, "count": len(results), "results": results}


# ─── Collect ──────────────────────────────────────────────────────────────
@router.post("/collect")
def youtube_collect(db: Session = Depends(get_db)):
    queries = settings.YOUTUBE_TRACKED_QUERIES
    if not queries:
        raise HTTPException(400, "YOUTUBE_TRACKED_QUERIES_RAW فارغ")
    stats = collector_svc.collect_all(db, queries)
    return {"status": "ok", **stats}


# ─── Tracked videos ───────────────────────────────────────────────────────
@router.get("/videos")
def youtube_videos(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return videos_svc.list_videos(db, limit=limit)


# ─── Rising ───────────────────────────────────────────────────────────────
@router.get("/rising")
def youtube_rising(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return videos_svc.list_rising(db, limit=limit)
