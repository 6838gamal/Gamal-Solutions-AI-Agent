import httpx
from datetime import datetime
from typing import List, Dict, Any
from app.core.config import settings

YT_API = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(Exception):
    pass


def _get(path: str, params: dict) -> dict:
    if not settings.YOUTUBE_API_KEY:
        raise YouTubeAPIError("YOUTUBE_API_KEY غير مُعرَّف")
    params = {**params, "key": settings.YOUTUBE_API_KEY}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{YT_API}/{path}", params=params)
    if r.status_code != 200:
        raise YouTubeAPIError(f"YouTube API {r.status_code}: {r.text[:200]}")
    return r.json()


def search_videos(query: str, max_results: int = 25) -> List[Dict[str, Any]]:
    data = _get("search", {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "order": "viewCount",
    })
    ids = [it["id"]["videoId"] for it in data.get("items", [])]
    if not ids:
        return []
    return get_videos_details(ids)


def get_videos_details(video_ids: List[str]) -> List[Dict[str, Any]]:
    data = _get("videos", {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids[:50]),
    })
    out = []
    for it in data.get("items", []):
        sn = it["snippet"]
        st = it.get("statistics", {})
        out.append({
            "youtube_id":    it["id"],
            "title":         sn.get("title", ""),
            "description":   sn.get("description", ""),
            "channel_youtube_id":    sn.get("channelId", ""),
            "channel_title":         sn.get("channelTitle", ""),
            "thumbnail_url": (sn.get("thumbnails", {}).get("medium", {}) or {}).get("url"),
            "published_at":  _parse_dt(sn.get("publishedAt")),
            "view_count":    int(st.get("viewCount", 0) or 0),
            "like_count":    int(st.get("likeCount", 0) or 0),
            "comment_count": int(st.get("commentCount", 0) or 0),
            "duration_sec":  _parse_duration(it.get("contentDetails", {}).get("duration")),
        })
    return out


def get_channels_details(channel_youtube_ids: List[str]) -> List[Dict[str, Any]]:
    data = _get("channels", {
        "part": "snippet,statistics",
        "id": ",".join(channel_youtube_ids[:50]),
    })
    out = []
    for it in data.get("items", []):
        sn = it["snippet"]
        st = it.get("statistics", {})
        out.append({
            "youtube_id":       it["id"],
            "title":            sn.get("title", ""),
            "description":      sn.get("description", ""),
            "country":          sn.get("country"),
            "published_at":     _parse_dt(sn.get("publishedAt")),
            "subscriber_count": int(st.get("subscriberCount", 0) or 0),
            "video_count":      int(st.get("videoCount", 0) or 0),
            "view_count":       int(st.get("viewCount", 0) or 0),
        })
    return out


def _parse_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _parse_duration(iso: str) -> int:
    """PT1H2M3S → 3723 ثانية."""
    if not iso:
        return 0
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + s
