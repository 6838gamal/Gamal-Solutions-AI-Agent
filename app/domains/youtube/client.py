"""
YouTube Data API v3 — low-level HTTP client.
لا يحتوي أي منطق أعمال. فقط يستدعي الـendpoints ويرجع JSON.
"""
import httpx
from typing import Optional
from app.core.config import settings


class YouTubeClientError(Exception):
    pass


class YouTubeClient:
    BASE = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 20):
        self.api_key = api_key or getattr(settings, "YOUTUBE_API_KEY", None)
        if not self.api_key:
            raise YouTubeClientError("YOUTUBE_API_KEY is not configured")
        self.timeout = timeout

    def _get(self, endpoint: str, **params) -> dict:
        params["key"] = self.api_key
        url = f"{self.BASE}/{endpoint}"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(url, params=params)
            if r.status_code >= 400:
                raise YouTubeClientError(f"{r.status_code}: {r.text[:300]}")
            return r.json()

    def search(self, q: str, max_results: int = 25, order: str = "relevance",
               published_after: Optional[str] = None) -> dict:
        params = {
            "part": "snippet",
            "q": q,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": order,
        }
        if published_after:
            params["publishedAfter"] = published_after
        return self._get("search", **params)

    def videos(self, video_ids: list[str]) -> dict:
        if not video_ids:
            return {"items": []}
        return self._get(
            "videos",
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids[:50]),
        )

    def channels(self, channel_ids: list[str]) -> dict:
        if not channel_ids:
            return {"items": []}
        return self._get(
            "channels",
            part="snippet,statistics",
            id=",".join(channel_ids[:50]),
        )
