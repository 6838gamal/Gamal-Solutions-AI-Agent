"""
Opportunity Engine — يربط topics + scoring، ويرتب الفرص.
"""
from sqlalchemy.orm import Session

from app.domains.youtube.services.topics import extract_topics
from app.domains.youtube.services.scoring import compute_opportunity


def get_opportunities(
    db: Session,
    limit: int = 50,
    min_videos: int = 3,
    min_demand: float = 0.0,
    max_competition: float = 100.0,
) -> list[dict]:
    """
    1. يستدعي extract_topics
    2. يحسب opportunity لكل topic
    3. يفلتر
    4. يرتب تنازليًا
    """
    topics = extract_topics(db, limit=1000, min_videos=min_videos)
    if not topics:
        return []

    scored = [compute_opportunity(t, topics) for t in topics]

    # فلترة
    filtered = [
        o for o in scored
        if o["demand"] >= min_demand and o["competition"] <= max_competition
    ]

    filtered.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return filtered[:limit]


def get_top_opportunity(db: Session) -> dict | None:
    """يرجع أعلى فرصة واحدة."""
    opps = get_opportunities(db, limit=1)
    return opps[0] if opps else None
