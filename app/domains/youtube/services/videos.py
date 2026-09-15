from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session, joinedload
from app.domains.youtube.models import (
    YouTubeVideo, YouTubeChannel, VideoSnapshot
)


# ─── قراءات أساسية ─────────────────────────────────────────────────

def get_video(db: Session, video_id: int) -> Optional[YouTubeVideo]:
    return (
        db.query(YouTubeVideo)
        .options(joinedload(YouTubeVideo.channel))
        .filter_by(id=video_id)
        .first()
    )


def list_videos(db: Session, limit: int = 50, offset: int = 0) -> List[YouTubeVideo]:
    return (
        db.query(YouTubeVideo)
        .options(joinedload(YouTubeVideo.channel))
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


# ─── Velocity (كما هي عندك) ────────────────────────────────────────

def compute_velocity(db: Session, video_id: int) -> dict:
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

    dv = (curr.view_count or 0) - (prev.view_count or 0)
    vph = dv / dt_hours
    gr = (dv / prev.view_count) if prev.view_count else None

    return {
        "views_per_hour": round(vph, 2),
        "growth_rate": round(gr, 4) if gr is not None else None,
        "acceleration": None,
    }


# ─── Serializer موحّد (مهم!) ────────────────────────────────────────

def serialize_video(v: YouTubeVideo, snap: Optional[VideoSnapshot] = None,
                    vel: Optional[dict] = None) -> dict:
    """يحوّل YouTubeVideo إلى dict يطابق ما يتوقعه Alpine."""
    snap = snap if snap is not None else latest_snapshot_for(v)
    data = {
        "id":            v.id,
        "youtube_id":    v.youtube_id,
        "title":         v.title,
        "description":   v.description,
        "channel_title": v.channel.title if v.channel else None,
        "channel_id":    v.channel.youtube_id if v.channel else None,
        "thumbnail_url": v.thumbnail_url,
        "published_at":  v.published_at.isoformat() if v.published_at else None,
        "duration_sec":  v.duration_sec,
        "query_source":  v.query_source,
        "view_count":    (snap.view_count if snap else 0) or 0,
        "like_count":    (snap.like_count if snap else 0) or 0,
        "comment_count": (snap.comment_count if snap else 0) or 0,
    }
    if vel:
        data["views_per_hour"] = vel.get("views_per_hour")
        data["growth_rate"]    = vel.get("growth_rate") or 0
        data["breakout_score"] = _breakout_score(vel, data["view_count"])
    return data


def latest_snapshot_for(v: YouTubeVideo) -> Optional[VideoSnapshot]:
    """يستخدم العلاقة المحمّلة مسبقًا إن وُجدت، وإلا يستعلم."""
    if not v.snapshots:
        return None
    return max(v.snapshots, key=lambda s: s.captured_at or datetime.min)


# ─── Counters للـ /stats ──────────────────────────────────────────

def count_videos(db: Session) -> int:
    return db.query(func.count(YouTubeVideo.id)).scalar() or 0


def count_channels(db: Session) -> int:
    return db.query(func.count(YouTubeChannel.id)).scalar() or 0


def count_snapshots(db: Session) -> int:
    return db.query(func.count(VideoSnapshot.id)).scalar() or 0


def count_rising(db: Session, min_velocity: float = 100.0,
                 within_hours: int = 48) -> int:
    """عدد الفيديوهات التي vph >= min_velocity خلال آخر within_hours."""
    since = datetime.utcnow() - timedelta(hours=within_hours)
    vids = (
        db.query(YouTubeVideo.id)
        .filter(YouTubeVideo.published_at >= since)
        .all()
    )
    n = 0
    for (vid_id,) in vids:
        vel = compute_velocity(db, vid_id)
        if vel["views_per_hour"] and vel["views_per_hour"] >= min_velocity:
            n += 1
    return n


# ─── Rising list ─────────────────────────────────────────────────

def list_rising(db: Session, limit: int = 20,
                within_hours: int = 48, min_velocity: float = 50.0) -> List[dict]:
    since = datetime.utcnow() - timedelta(hours=within_hours)
    candidates = (
        db.query(YouTubeVideo)
        .options(joinedload(YouTubeVideo.channel), joinedload(YouTubeVideo.snapshots))
        .filter(YouTubeVideo.published_at >= since)
        .order_by(YouTubeVideo.published_at.desc())
        .limit(500)
        .all()
    )
    enriched = []
    for v in candidates:
        vel = compute_velocity(db, v.id)
        if not vel["views_per_hour"] or vel["views_per_hour"] < min_velocity:
            continue
        snap = latest_snapshot_for(v)
        enriched.append(serialize_video(v, snap=snap, vel=vel))

    enriched.sort(key=lambda x: x.get("views_per_hour") or 0, reverse=True)
    return enriched[:limit]


def _breakout_score(vel: dict, view_count: int) -> float:
    """0–100: مزيج من vph و growth."""
    vph = vel.get("views_per_hour") or 0
    gr  = vel.get("growth_rate")  or 0
    score = min(60, (vph / 1000) * 10)
    score += min(40, gr * 800)
    return round(score, 1)
