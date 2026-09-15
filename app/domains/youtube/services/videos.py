from typing import Optional, List
from sqlalchemy.orm import Session
from app.domains.youtube.models import YouTubeVideo, VideoSnapshot


def get_video(db: Session, video_id: int) -> Optional[YouTubeVideo]:
    return db.query(YouTubeVideo).filter_by(id=video_id).first()


def list_videos(db: Session, limit: int = 50, offset: int = 0) -> List[YouTubeVideo]:
    return (
        db.query(YouTubeVideo)
        .order_by(YouTubeVideo.published_at.desc().nullslast())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_snapshots(db: Session, video_id: int, limit: int = 200) -> List[VideoSnapshot]:
    return (
        db.query(VideoSnapshot)
        .filter_by(video_id=video_id)
        .order_by(VideoSnapshot.captured_at.asc())
        .limit(limit)
        .all()
    )


def latest_snapshot(db: Session, video_id: int) -> Optional[VideoSnapshot]:
    return (
        db.query(VideoSnapshot)
        .filter_by(video_id=video_id)
        .order_by(VideoSnapshot.captured_at.desc())
        .first()
    )


def compute_velocity(db: Session, video_id: int) -> dict:
    """
    يحسب views_per_hour و growth_rate من آخر snapshot-ين.
    """
    snaps = (
        db.query(VideoSnapshot)
        .filter_by(video_id=video_id)
        .order_by(VideoSnapshot.captured_at.desc())
        .limit(2)
        .all()
    )
    if len(snaps) < 2:
        return {"views_per_hour": None, "growth_rate": None, "acceleration": None}

    curr, prev = snaps[0], snaps[1]
    dt_hours = (curr.captured_at - prev.captured_at).total_seconds() / 3600
    if dt_hours <= 0:
        return {"views_per_hour": None, "growth_rate": None, "acceleration": None}

    dv = curr.view_count - prev.view_count
    vph = dv / dt_hours
    gr = (dv / prev.view_count) if prev.view_count else None

    return {
        "views_per_hour": round(vph, 2),
        "growth_rate": round(gr, 4) if gr is not None else None,
        "acceleration": None,   # يحتاج 3 snapshots على الأقل
    }
