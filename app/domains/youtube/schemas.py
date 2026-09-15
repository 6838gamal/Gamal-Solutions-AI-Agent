from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ChannelOut(BaseModel):
    id: int
    youtube_id: str
    title: Optional[str] = None
    subscriber_count: Optional[int] = 0
    video_count: Optional[int] = 0

    class Config:
        from_attributes = True


class VideoSnapshotOut(BaseModel):
    id: int
    view_count: int
    like_count: int
    comment_count: int
    captured_at: datetime

    class Config:
        from_attributes = True


class VideoOut(BaseModel):
    id: int
    youtube_id: str
    title: str
    channel_id: Optional[int] = None
    channel_title: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_sec: Optional[int] = None
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None

    class Config:
        from_attributes = True


class VideoDetailOut(VideoOut):
    description: Optional[str] = None
    tags: List[str] = []
    query_source: Optional[str] = None
    snapshots: List[VideoSnapshotOut] = []


class SearchResultOut(BaseModel):
    query: str
    results: List[VideoOut]
    cached: bool = False
    count: int = 0
