from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.domains.youtube.schemas import (
    VideoOut, VideoDetailOut, SearchResultOut, VideoSnapshotOut
)
from app.domains.youtube.services import search as search_svc
from app.domains.youtube.services import videos as videos_svc

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/search", response_model=SearchResultOut)
def youtube_search(
    q: str = Query(..., min_length=2),
    max_results: int = Query(25, ge=1, le=50),
    persist: bool = Query(True),
    db: Session = Depends(get_db),
):
    """ابحث في YouTube. عند persist=True يخزّن النتائج + snapshot أولي."""
    try:
        if persist:
            stored = search_svc.search_and_store(db, q=q, max_results=max_results)
            results = [_video_to_out(v) for v in stored]
        else:
            from app.domains.youtube.client import YouTubeClient
            client = YouTubeClient()
            resp = client.search(q=q, max_results=max_results)
            results = [
                VideoOut(
                    id=0,
                    youtube_id=it["id"]["videoId"],
                    title=it["snippet"]["title"],
                    channel_title=it["snippet"].get("channelTitle"),
                    published_at=None,
                )
                for it in resp.get("items", [])
            ]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"YouTube API error: {e}")

    return SearchResultOut(
        query=q, results=results, cached=False, count=len(results)
    )


@router.get("/videos", response_model=List[VideoOut])
def list_videos(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return [_video_to_out(v) for v in videos_svc.list_videos(db, limit, offset)]


@router.get("/videos/{video_id}", response_model=VideoDetailOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    v = videos_svc.get_video(db, video_id)
    if not v:
        raise HTTPException(404, "video not found")
    snaps = videos_svc.get_snapshots(db, video_id)
    return VideoDetailOut(
        **_video_to_out(v).dict(),
        description=v.description,
        tags=v.tags or [],
        query_source=v.query_source,
        snapshots=[VideoSnapshotOut.from_orm(s) for s in snaps],
    )


@router.get("/videos/{video_id}/snapshots", response_model=List[VideoSnapshotOut])
def get_video_snapshots(video_id: int, db: Session = Depends(get_db)):
    return videos_svc.get_snapshots(db, video_id)


@router.get("/videos/{video_id}/velocity")
def get_video_velocity(video_id: int, db: Session = Depends(get_db)):
    return videos_svc.compute_velocity(db, video_id)


@router.post("/collect")
def trigger_collect():
    """يشغّل دورة جمع يدويًا (في نفس الـthread، بدون background)."""
    from app.domains.youtube.collector import run_collection_once
    run_collection_once()
    return {"status": "ok"}


# ── Helpers ────────────────────────────────────────────────────────────

def _video_to_out(v) -> VideoOut:
    latest = v.snapshots[-1] if v.snapshots else None
    return VideoOut(
        id=v.id,
        youtube_id=v.youtube_id,
        title=v.title,
        channel_id=v.channel_id,
        channel_title=v.channel.title if v.channel else None,
        published_at=v.published_at,
        duration_sec=v.duration_sec,
        thumbnail_url=v.thumbnail_url,
        view_count=latest.view_count if latest else None,
        like_count=latest.like_count if latest else None,
        comment_count=latest.comment_count if latest else None,
    )
