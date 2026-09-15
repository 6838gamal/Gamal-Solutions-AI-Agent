"""
Collector — يعمل في thread داخل startup() بنفس نمط telegram_auto_sync.
كل 30 دقيقة: يجمع نتائج كل tracked query ويخزن snapshots جديدة.
"""
import time
from datetime import datetime
from app.core.database import SessionLocal
from app.domains.youtube.services.search import search_and_store
from app.domains.youtube.models import YouTubeVideo, VideoSnapshot
from app.core.config import settings


def _refresh_snapshots_for_recent(db, hours: int = 48, limit: int = 100):
    """
    يحدّث الـsnapshots للفيديوهات الحديثة (آخر 48 ساعة).
    """
    from app.domains.youtube.client import YouTubeClient
    from sqlalchemy import desc

    cutoff = datetime.utcnow().replace(microsecond=0)
    # آخر N فيديو من قاعدة البيانات
    videos = (
        db.query(YouTubeVideo)
        .order_by(desc(YouTubeVideo.created_at))
        .limit(limit)
        .all()
    )
    if not videos:
        return 0

    # جمّعهم في batches من 50
    ids = [v.youtube_id for v in videos]
    id_to_video = {v.youtube_id: v for v in videos}

    client = YouTubeClient()
    added = 0
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        try:
            resp = client.videos(batch)
        except Exception as e:
            print(f"[YouTubeCollector] videos.list error: {e}")
            continue

        now = datetime.utcnow()
        for item in resp.get("items", []):
            stats = item.get("statistics", {}) or {}
            v = id_to_video.get(item["id"])
            if not v:
                continue
            db.add(VideoSnapshot(
                video_id=v.id,
                view_count=int(stats.get("viewCount") or 0),
                like_count=int(stats.get("likeCount") or 0),
                comment_count=int(stats.get("commentCount") or 0),
                captured_at=now,
            ))
            added += 1
    db.commit()
    return added


def run_collection_once():
    db = SessionLocal()
    try:
        queries = getattr(settings, "YOUTUBE_TRACKED_QUERIES", []) or []
        for q in queries:
            try:
                stored = search_and_store(db, q=q, max_results=25)
                print(f"[YouTubeCollector] '{q}': {len(stored)} videos upserted")
            except Exception as e:
                print(f"[YouTubeCollector] search '{q}' failed: {e}")

        refreshed = _refresh_snapshots_for_recent(db, hours=48, limit=100)
        print(f"[YouTubeCollector] {refreshed} snapshots added")
    finally:
        db.close()


def youtube_auto_collect(interval_sec: int = 30 * 60, initial_delay: int = 30):
    """Thread target — يُشغَّل من startup()."""
    time.sleep(initial_delay)
    print(f"[YouTubeCollector] بدأ — كل {interval_sec // 60} دقيقة")
    while True:
        try:
            run_collection_once()
        except Exception as e:
            print(f"[YouTubeCollector] outer error: {e}")
        time.sleep(interval_sec)
