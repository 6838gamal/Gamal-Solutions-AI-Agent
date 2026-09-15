from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, DateTime,
    ForeignKey, Index, func
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base


class YouTubeChannel(Base):
    __tablename__ = "youtube_channels"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    youtube_id       = Column(String(64), unique=True, nullable=False, index=True)
    title            = Column(String(500))
    description      = Column(Text)
    subscriber_count = Column(BigInteger, default=0)
    video_count      = Column(Integer, default=0)
    view_count       = Column(BigInteger, default=0)
    country          = Column(String(10))
    published_at     = Column(DateTime)
    created_at       = Column(DateTime, server_default=func.now())
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())

    videos = relationship("YouTubeVideo", back_populates="channel", cascade="all, delete-orphan")


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    youtube_id    = Column(String(64), unique=True, nullable=False, index=True)
    channel_id    = Column(BigInteger, ForeignKey("youtube_channels.id", ondelete="CASCADE"), index=True)
    title         = Column(String(500), nullable=False)
    description   = Column(Text)
    published_at  = Column(DateTime, index=True)
    duration_sec  = Column(Integer)
    category_id   = Column(String(20))
    tags          = Column(ARRAY(String), default=list)
    thumbnail_url = Column(String(500))
    query_source  = Column(String(255), index=True)   # الكويري الذي جاء منه الفيديو
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())

    channel   = relationship("YouTubeChannel", back_populates="videos")
    snapshots = relationship(
        "VideoSnapshot",
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="VideoSnapshot.captured_at",
    )

    __table_args__ = (
        Index("ix_youtube_videos_channel_published", "channel_id", "published_at"),
    )


class VideoSnapshot(Base):
    __tablename__ = "video_snapshots"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id      = Column(BigInteger, ForeignKey("youtube_videos.id", ondelete="CASCADE"), nullable=False)
    view_count    = Column(BigInteger, default=0)
    like_count    = Column(BigInteger, default=0)
    comment_count = Column(BigInteger, default=0)
    captured_at   = Column(DateTime, server_default=func.now(), index=True)

    video = relationship("YouTubeVideo", back_populates="snapshots")

    __table_args__ = (
        Index("ix_video_snapshots_video_captured", "video_id", "captured_at"),
    )
