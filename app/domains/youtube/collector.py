"""
Collector — يعمل في thread داخل startup() بنفس نمط telegram_auto_sync.
كل 30 دقيقة: يجمع نتائج كل tracked query ويخزن snapshots جديدة.

الإصلاحات:
  • initial_delay الافتراضي = 30 دقيقة لمنع الازدواج مع أول جمع يدوي.
  • Snapshot dedup: لا snapshot جديد لنفس الفيديو قبل مرور MIN_INTERVAL_MINUTES.
"""
import time
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.domains.youtube.services.search import search_and_store
from app.domains.youtube.models import YouTubeVideo, VideoSnapshot
from app.core.config import settings


# لا snapshot جديد لنفس الفيديو قبل مرور هذه المدة
MIN_INTERVAL_MINUTES = 25


def _refresh_snapshots_for_recent(db, hours: int = 48, limit: int = 100):
    """
    يحدّث الـsnapshots للفيديوهات الحديثة (آخر 48 ساعة).

    لكن فقط للفيديوهات التي مرّ على آخر snapshot لها MIN_INTERVAL_MINUTES
    على الأقل. هذا يمنع تكرار الـsnapshots عند تشغيل الـcollector يدويًا
    ثم تلقائيًا بعد دقائق.
    """
    from app.domains.youtube.client import YouTubeClient
    from sqlalchemy import desc

    cutoff = datetime.utcnow() - timedelta(minutes=MIN_INTERVAL_MINUTES)

    # آخر N فيديو من قاعدة البيانات
    videos = (
        db.query(YouTubeVideo)
        .order_by(desc(YouTubeVideo.created_at))
        .limit(limit)
        .all()
    )
    if not videos:
        return 0

    # فلترة: احتفظ فقط بالفيديوهات التي آخر snapshot لها قديم بما يكفي
    video_ids_to_refresh: list[str] = []
    id_to_video: dict[str, YouTubeVideo] = {}

    for v in videos:
        latest = (
            db.query(VideoSnapshot)
            .filter_by(video_id=v.id)
            .order_by(VideoSnapshot.captured_at.desc())
            .first()
        )
        if latest is None or latest.captured_at < cutoff:
            video_ids_to_refresh.append(v.youtube_id)
            id_to_video[v.youtube_id] = v

    if not video_ids_to_refresh:
        print(f"[YouTubeCollector] no videos need refresh (all snapshots fresh < {MIN_INTERVAL_MINUTES}min)")
        return 0

    # جمّعهم في batches من 50
    client = YouTubeClient()
    added = 0
    for i in range(0, len(video_ids_to_refresh), 50):
        batch = video_ids_to_refresh[i:i + 50]
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
        max_results = getattr(settings, "YOUTUBE_MAX_RESULTS_PER_QUERY", 25)
        snapshot_limit = getattr(settings, "YOUTUBE_SNAPSHOT_REFRESH_LIMIT", 100)

        for q in queries:
            try:
                stored = search_and_store(db, q=q, max_results=max_results)
                print(f"[YouTubeCollector] '{q}': {len(stored)} videos upserted")
            except Exception as e:
                print(f"[YouTubeCollector] search '{q}' failed: {e}")

        refreshed = _refresh_snapshots_for_recent(db, hours=48, limit=snapshot_limit)
        print(f"[YouTubeCollector] {refreshed} snapshots added")
    finally:
        db.close()


def youtube_auto_collect(interval_sec: int = 30 * 60, initial_delay: int = 30 * 60):
    """
    Thread target — يُشغَّل من startup().

    initial_delay الافتراضي = 30 دقيقة (وليس 30 ثانية) لتجنب الازدواج
    مع أول جمع يدوي عند الإقلاع.
    """
    time.sleep(initial_delay)
    print(f"[YouTubeCollector] بدأ — كل {interval_sec // 60} دقيقة")
    while True:
        try:
            run_collection_once()
        except Exception as e:
            print(f"[YouTubeCollector] outer error: {e}")
        time.sleep(interval_sec)
