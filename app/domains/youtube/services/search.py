"""
YouTube search + persistence.
يرجع النتائج، ويخزّن الفيديوهات + القنوات + Snapshot أولي.
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.domains.youtube.client import YouTubeClient
from app.domains.youtube.models import YouTubeChannel, YouTubeVideo, VideoSnapshot


def _parse_duration(iso: str) -> int:
    """PT1H2M3S → seconds."""
    import re
    if not iso:
        return 0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def _parse_dt(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _upsert_channel(db: Session, item: dict) -> YouTubeChannel:
    yt_id = item["id"]
    stats = item.get("statistics", {}) or {}
    snippet = item.get("snippet", {}) or {}

    ch = db.query(YouTubeChannel).filter_by(youtube_id=yt_id).first()
    if not ch:
        ch = YouTubeChannel(youtube_id=yt_id)
        db.add(ch)

    ch.title            = snippet.get("title") or ch.title
    ch.description      = snippet.get("description") or ch.description
    ch.subscriber_count = int(stats.get("subscriberCount") or 0)
    ch.video_count      = int(stats.get("videoCount") or 0)
    ch.view_count       = int(stats.get("viewCount") or 0)
    ch.country          = snippet.get("country") or ch.country
    ch.published_at     = _parse_dt(snippet.get("publishedAt")) or ch.published_at

    db.flush()
    return ch


def _upsert_video(db: Session, item: dict, channel: YouTubeChannel,
                  query_source: str | None = None) -> YouTubeVideo:
    yt_id = item["id"]
    snippet = item.get("snippet", {}) or {}
    stats = item.get("statistics", {}) or {}
    content = item.get("contentDetails", {}) or {}

    v = db.query(YouTubeVideo).filter_by(youtube_id=yt_id).first()
    if not v:
        v = YouTubeVideo(youtube_id=yt_id)
        db.add(v)

    v.channel_id    = channel.id
    v.title         = snippet.get("title") or v.title
    v.description   = snippet.get("description") or v.description
    v.published_at  = _parse_dt(snippet.get("publishedAt")) or v.published_at
    v.duration_sec  = _parse_duration(content.get("duration")) or v.duration_sec
    v.category_id   = snippet.get("categoryId") or v.category_id
    v.tags          = snippet.get("tags") or v.tags or []
    v.thumbnail_url = (
        (snippet.get("thumbnails", {}).get("high") or {}).get("url")
        or v.thumbnail_url
    )
    if query_source:
        v.query_source = query_source

    db.flush()

    # snapshot أولي
    if stats:
        snap = VideoSnapshot(
            video_id=v.id,
            view_count=int(stats.get("viewCount") or 0),
            like_count=int(stats.get("likeCount") or 0),
            comment_count=int(stats.get("commentCount") or 0),
            captured_at=datetime.utcnow(),
        )
        db.add(snap)

    return v


def search_and_store(db: Session, q: str, max_results: int = 25) -> List[YouTubeVideo]:
    client = YouTubeClient()

    # 1) search.list
    search_resp = client.search(q=q, max_results=max_results, order="relevance")
    items = search_resp.get("items", [])
    if not items:
        return []

    video_ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]
    channel_ids = list({
        it["snippet"]["channelId"] for it in items
        if it.get("snippet", {}).get("channelId")
    })

    # 2) videos.list
    videos_resp = client.videos(video_ids)
    video_items = videos_resp.get("items", [])

    # 3) channels.list
    channels_resp = client.channels(channel_ids)
    channel_items = {c["id"]: c for c in channels_resp.get("items", [])}

    # 4) upsert channels
    channel_map = {}
    for cid in channel_ids:
        c_item = channel_items.get(cid)
        if c_item:
            channel_map[cid] = _upsert_channel(db, c_item)

    # 5) upsert videos
    stored: List[YouTubeVideo] = []
    for item in video_items:
        cid = item["snippet"]["channelId"]
        ch = channel_map.get(cid)
        if not ch:
            # fallback: minimal channel
            ch = YouTubeChannel(
                youtube_id=cid,
                title=item["snippet"].get("channelTitle"),
            )
            db.add(ch)
            db.flush()
            channel_map[cid] = ch
        stored.append(_upsert_video(db, item, ch, query_source=q))

    db.commit()
    return stored
