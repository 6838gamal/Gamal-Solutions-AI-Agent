"""
Topic Aggregation — تجميع العناوين المتشابهة في Topics.

يعمل على البيانات المخزَّنة فقط (لا يستدعي YouTube API).
يستخرج keywords من كل عنوان، يطبّعها، ويجمّع العناوين المتشابهة.
"""
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.domains.youtube.models import YouTubeVideo, YouTubeChannel, VideoSnapshot


# ══════════════════════════════════════════════════════════════════
# Stopwords — كلمات عامة لا تعبّر عن موضوع
# ══════════════════════════════════════════════════════════════════
STOPWORDS_EN = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else",
    "of", "to", "in", "on", "at", "by", "for", "with", "about",
    "from", "into", "through", "during", "before", "after",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "should", "could", "can", "may", "might",
    "i", "you", "he", "she", "it", "we", "they",
    "my", "your", "his", "her", "its", "our", "their",
    "this", "that", "these", "those",
    "what", "which", "who", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very",
    "just", "now", "here", "there", "up", "down", "out", "off",
    "get", "got", "make", "made", "use", "used", "using",
    "vs", "via", "per", "new", "best", "top", "full", "free",
    "2024", "2025", "2026", "2027",
}

STOPWORDS_AR = {
    "في", "من", "إلى", "على", "عن", "مع", "هذا", "هذه", "ذلك", "تلك",
    "التي", "الذي", "الذين", "ما", "ماذا", "كيف", "لماذا", "متى", "أين",
    "هل", "ثم", "أو", "و", "لكن", "بل", "حتى", "قد", "كان", "كانت",
    "يكون", "تكون", "هو", "هي", "هم", "هن", "أنا", "أنت", "نحن",
    "كل", "بعض", "أي", "لا", "لم", "لن", "إن", "أن", "إذا",
    "بعد", "قبل", "بين", "خلال", "حول", "ضد", "حسب", "عبر",
    "الأول", "الأخير", "الجديد", "القديم", "أفضل", "أكبر", "أصغر",
    "شرح", "درس", "كورس", "دورة", "مقدمة", "طريقة", "طرق",
}

ALL_STOPWORDS = STOPWORDS_EN | STOPWORDS_AR


# ══════════════════════════════════════════════════════════════════
# استخراج وتطبيع الكلمات
# ══════════════════════════════════════════════════════════════════

def normalize_word(word: str) -> str:
    """تطبيع الكلمة: lowercase + إزالة التشكيل + إزالة الرموز."""
    word = word.lower().strip()
    # إزالة التشكيل العربي
    word = re.sub(r"[\u064B-\u0652]", "", word)
    # إزالة الرموز
    word = re.sub(r"[^\w\u0600-\u06FF]", "", word)
    return word


def extract_keywords(title: str) -> list[str]:
    """
    يستخرج الكلمات المفتاحية من عنوان واحد.
    يرجع الكلمات المفردة + bigrams (كلمتين متتاليتين).
    """
    if not title:
        return []

    # تقسيم على المسافات والرموز
    tokens = re.split(r"[\s\-_|:,.!?()\[\]{}]+", title.lower())
    tokens = [normalize_word(t) for t in tokens if t]

    # فلترة stopwords والكلمات القصيرة
    keywords = [
        t for t in tokens
        if t and t not in ALL_STOPWORDS and len(t) > 2
    ]

    # bigrams (كلمتين متتاليتين)
    bigrams = []
    for i in range(len(keywords) - 1):
        bigrams.append(f"{keywords[i]} {keywords[i+1]}")

    return keywords + bigrams


# ══════════════════════════════════════════════════════════════════
# التجميع في Topics
# ══════════════════════════════════════════════════════════════════

def _get_latest_snapshot(db: Session, video_id: int) -> Optional[VideoSnapshot]:
    """يرجع آخر snapshot لفيديو معين."""
    return (
        db.query(VideoSnapshot)
        .filter_by(video_id=video_id)
        .order_by(VideoSnapshot.captured_at.desc())
        .first()
    )


def _get_earliest_snapshot(db: Session, video_id: int) -> Optional[VideoSnapshot]:
    """يرجع أول snapshot لفيديو معين."""
    return (
        db.query(VideoSnapshot)
        .filter_by(video_id=video_id)
        .order_by(VideoSnapshot.captured_at.asc())
        .first()
    )


def _compute_video_velocity(db: Session, video_id: int) -> Optional[float]:
    """
    يحسب views_per_hour من أول وآخر snapshot.
    يرجع None لو لا يوجد snapshot-ين بفاصل زمني كافٍ.
    """
    first = _get_earliest_snapshot(db, video_id)
    last = _get_latest_snapshot(db, video_id)
    if not first or not last or first.id == last.id:
        return None

    hours = (last.captured_at - first.captured_at).total_seconds() / 3600
    if hours < 0.5:  # أقل من 30 دقيقة — غير موثوق
        return None

    return (last.view_count - first.view_count) / hours


def extract_topics(db: Session, limit: int = 500, min_videos: int = 3) -> list[dict]:
    """
    الدالة الرئيسية.

    1. اجلب آخر limit فيديو
    2. استخرج keywords من كل عنوان
    3. جمّعهم في clusters بناءً على الكلمات المشتركة
    4. احسب إحصائيات لكل cluster
    5. ارجع فقط clusters مع min_videos على الأقل

    المخرجات: قائمة من dict، كل واحد يمثل topic.
    """
    # 1. اجلب الفيديوهات
    videos = (
        db.query(YouTubeVideo)
        .order_by(YouTubeVideo.created_at.desc())
        .limit(limit)
        .all()
    )
    if not videos:
        return []

    # 2. استخرج keywords لكل فيديو
    video_data = []
    for v in videos:
        keywords = extract_keywords(v.title or "")
        if not keywords:
            continue

        latest = _get_latest_snapshot(db, v.id)
        if not latest:
            continue

        velocity = _compute_video_velocity(db, v.id)
        subs = v.channel.subscriber_count if v.channel else 0

        # breakout = views / subscribers
        breakout = None
        if subs and subs > 0:
            breakout = latest.view_count / subs

        # engagement = (likes + comments) / views
        engagement = None
        if latest.view_count > 0:
            engagement = (latest.like_count + latest.comment_count) / latest.view_count

        video_data.append({
            "video": v,
            "keywords": keywords,
            "views": latest.view_count,
            "likes": latest.like_count,
            "comments": latest.comment_count,
            "velocity": velocity,
            "breakout": breakout,
            "engagement": engagement,
            "published_at": v.published_at,
            "channel_id": v.channel_id,
            "channel_subs": subs,
        })

    if not video_data:
        return []

    # 3. التجميع — كل keyword يصبح cluster، والفيديو قد ينتمي لعدة clusters
    clusters: dict[str, list] = defaultdict(list)

    for item in video_data:
        # استخدم أول 3 keywords أساسية (المفردة، ليس bigrams) كـ"مفتاح"
        # هذا يمنع clusters ضخمة جدًا
        primary_kws = [k for k in item["keywords"] if " " not in k][:3]
        for kw in primary_kws:
            clusters[kw].append(item)

    # 4. احسب إحصائيات لكل cluster
    topics = []
    for keyword, items in clusters.items():
        if len(items) < min_videos:
            continue

        views_list = [it["views"] for it in items if it["views"]]
        velocity_list = [it["velocity"] for it in items if it["velocity"] is not None]
        breakout_list = [it["breakout"] for it in items if it["breakout"] is not None]
        engagement_list = [it["engagement"] for it in items if it["engagement"] is not None]
        unique_channels = {it["channel_id"] for it in items}
        unique_channel_sizes = [it["channel_subs"] for it in items if it["channel_subs"]]

        # آخر تاريخ نشر
        pub_dates = [it["published_at"] for it in items if it["published_at"]]
        latest_published = max(pub_dates) if pub_dates else None
        days_since_latest = None
        if latest_published:
            days_since_latest = (datetime.utcnow() - latest_published).days

        # عينات العناوين (الأعلى مشاهدات)
        sorted_items = sorted(items, key=lambda x: x["views"] or 0, reverse=True)
        sample_titles = [it["video"].title for it in sorted_items[:5]]

        # كلمات مصاحبة (co-occurring keywords)
        co_keywords = Counter()
        for it in items:
            for kw in it["keywords"]:
                if kw != keyword and " " in kw:  # فقط bigrams للوضوح
                    co_keywords[kw] += 1

        topics.append({
            "topic": keyword,
            "topic_display": keyword.title(),
            "videos_count": len(items),
            "channels_count": len(unique_channels),
            "avg_views": sum(views_list) / len(views_list) if views_list else 0,
            "median_views": sorted(views_list)[len(views_list) // 2] if views_list else 0,
            "max_views": max(views_list) if views_list else 0,
            "avg_velocity": sum(velocity_list) / len(velocity_list) if velocity_list else 0,
            "avg_breakout": sum(breakout_list) / len(breakout_list) if breakout_list else 0,
            "avg_engagement": sum(engagement_list) / len(engagement_list) if engagement_list else 0,
            "avg_channel_size": (
                sum(unique_channel_sizes) / len(unique_channel_sizes)
                if unique_channel_sizes else 0
            ),
            "latest_published": latest_published.isoformat() if latest_published else None,
            "days_since_latest": days_since_latest,
            "sample_titles": sample_titles,
            "co_keywords": [k for k, _ in co_keywords.most_common(5)],
        })

    # 5. رتّب حسب عدد الفيديوهات
    topics.sort(key=lambda t: t["videos_count"], reverse=True)
    return topics


def get_topic_detail(db: Session, topic_name: str) -> Optional[dict]:
    """تفاصيل topic معين + الفيديوهات المرتبطة به."""
    all_topics = extract_topics(db, limit=1000)
    topic = next((t for t in all_topics if t["topic"] == topic_name.lower()), None)
    if not topic:
        return None

    # اجلب الفيديوهات المرتبطة
    videos = (
        db.query(YouTubeVideo)
        .filter(YouTubeVideo.title.ilike(f"%{topic_name}%"))
        .order_by(YouTubeVideo.published_at.desc())
        .limit(20)
        .all()
    )

    topic["videos"] = [
        {
            "id": v.id,
            "youtube_id": v.youtube_id,
            "title": v.title,
            "channel_title": v.channel.title if v.channel else None,
            "published_at": v.published_at.isoformat() if v.published_at else None,
            "thumbnail_url": v.thumbnail_url,
        }
        for v in videos
    ]
    return topic

