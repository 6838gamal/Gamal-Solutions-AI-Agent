"""
YouTube REST API — يستهلكه Alpine في youtube.html.
كل المسارات تحت /api/v1/youtube
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.config import settings
from app.domains.youtube.models import YouTubeVideo
from app.domains.youtube.services import videos as videos_svc
from app.domains.youtube import collector as collector_svc
from app.domains.youtube.services.search import search_and_store

router = APIRouter(prefix="/api/v1/youtube", tags=["youtube-api"])


# ══════════════════════════════════════════════════════════════════════
# GET /api/v1/youtube/stats
# ══════════════════════════════════════════════════════════════════════

@router.get("/stats")
def youtube_stats(db: Session = Depends(get_db)):
    return {
        "videos":    videos_svc.count_videos(db),
        "channels":  videos_svc.count_channels(db),
        "snapshots": videos_svc.count_snapshots(db),
        "rising":    videos_svc.count_rising(db, min_velocity=100),
    }


# ══════════════════════════════════════════════════════════════════════
# GET /api/v1/youtube/search
# ══════════════════════════════════════════════════════════════════════

@router.get("/search")
def youtube_search(
    q: str = Query(..., min_length=2),
    max_results: int = Query(25, ge=1, le=50),
    persist: bool = Query(True),
    db: Session = Depends(get_db),
):
    if not getattr(settings, "YOUTUBE_API_KEY", None):
        raise HTTPException(400, "YOUTUBE_API_KEY غير مُعرَّف في البيئة")

    try:
        stored = search_and_store(db, q=q, max_results=max_results)

        # أعِد تحميلهم مع joinedload لتفادي N+1
        if stored:
            ids = [v.id for v in stored]
            rows = (
                db.query(YouTubeVideo)
                .options(
                    joinedload(YouTubeVideo.channel),
                    joinedload(YouTubeVideo.snapshots),
                )
                .filter(YouTubeVideo.id.in_(ids))
                .all()
            )
            results = [
                videos_svc.serialize_video(
                    v,
                    snap=videos_svc.latest_snapshot_for(v),
                )
                for v in rows
            ]
        else:
            results = []

    except Exception as e:
        raise HTTPException(502, f"YouTube error: {e}")

    return {"query": q, "count": len(results), "results": results}


# ══════════════════════════════════════════════════════════════════════
# POST /api/v1/youtube/collect
# ══════════════════════════════════════════════════════════════════════

@router.post("/collect")
def youtube_collect(db: Session = Depends(get_db)):
    queries = getattr(settings, "YOUTUBE_TRACKED_QUERIES", []) or []
    if not queries:
        raise HTTPException(
            400,
            "YOUTUBE_TRACKED_QUERIES_RAW فارغ — أضفه في Render → Environment"
        )

    try:
        result = collector_svc.collect_all(db, queries)
    except Exception as e:
        raise HTTPException(500, f"Collector error: {e}")

    return {"status": "ok", **result}


# ══════════════════════════════════════════════════════════════════════
# GET /api/v1/youtube/videos
# ══════════════════════════════════════════════════════════════════════

@router.get("/videos")
def youtube_videos(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = videos_svc.list_videos(db, limit=limit)
    return [
        videos_svc.serialize_video(
            v,
            snap=videos_svc.latest_snapshot_for(v),
        )
        for v in rows
    ]


# ══════════════════════════════════════════════════════════════════════
# GET /api/v1/youtube/rising
# ══════════════════════════════════════════════════════════════════════

@router.get("/rising")
def youtube_rising(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # list_rising تُرجع list[dict] جاهزة
    return videos_svc.list_rising(db, limit=limit)
