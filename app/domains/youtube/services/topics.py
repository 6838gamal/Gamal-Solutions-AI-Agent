"""
Topic Aggregation — تجميع العناوين المتشابهة في Topics.

النسخة 3:
  • استعلامات مُجمَّعة (3 استعلامات بدل 2260) — أسرع 50-100x
  • bigrams فقط
  • stopwords عربية موسّعة
  • min_videos افتراضي = 2
"""
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.youtube.models import YouTubeVideo, YouTubeChannel, VideoSnapshot


# ══════════════════════════════════════════════════════════════════
# Stopwords
# ══════════════════════════════════════════════════════════════════

STOPWORDS_EN = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else",
    "of", "to", "in", "on", "at", "by", "for", "with", "about",
    "from", "into", "through", "during", "before", "after",
    "over", "under", "between", "without", "within",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "should", "could", "can", "may", "might",
    "get", "got", "make", "made", "use", "used", "using",
    "learn", "learning", "watch", "watching", "see", "saw",
    "know", "knew", "want", "wanted", "need", "needed",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "there",
    "what", "which", "who", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very",
    "just", "now", "here", "up", "down", "out", "off",
    "vs", "via", "per", "new", "old",
    "best", "top", "full", "free", "pro", "vs.",
    "2024", "2025", "2026", "2027",
    "tutorial", "guide", "course", "lesson", "review",
    "intro", "introduction", "beginner", "beginners",
    "complete", "ultimate", "definitive", "essential",
    "explained", "explain", "understanding", "learn",
    "step", "steps", "tips", "tricks", "hacks",
    "part", "episode", "video", "videos",
    "shorts", "short", "clip", "clips",
    "update", "updated", "news",
    "easy", "simple", "quick", "fast",
    "real", "actually", "really", "finally",
    "everywhere",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
}

STOPWORDS_AR = {
    "في", "من", "إلى", "على", "عن", "مع", "حتى", "منذ", "خلال",
    "بين", "أمام", "خلف", "فوق", "تحت", "حول", "ضد", "حسب",
    "عبر", "نحو", "لدى", "بعد", "قبل",
    "هو", "هي", "هم", "هن", "أنا", "أنت", "نحن", "إياه", "إياها",
    "هذا", "هذه", "ذلك", "تلك", "هؤلاء", "أولئك",
    "التي", "الذي", "الذين", "اللاتي",
    "ما", "ماذا", "كيف", "لماذا", "متى", "أين", "هل",
    "ثم", "أو", "و", "لكن", "بل", "قد", "كان", "كانت",
    "يكون", "تكون", "ليس", "ليست",
    "إن", "أن", "إذا", "لو", "لولا",
    "لا", "لم", "لن",
    "كل", "بعض", "أي", "جميع", "معظم", "كثير", "قليل",
    "الأول", "الأخير", "الجديد", "القديم", "أفضل", "أكبر", "أصغر",
    "شرح", "درس", "دورة", "كورس", "مقدمة", "طريقة", "طرق",
    "خطوات", "نصائح", "حيل", "أسرار",
    "كامل", "كاملة", "شامل", "بسيط", "سهل", "سريع",
    "الحلقة", "الجزء", "فيديو", "شورت", "تحديث", "أخبار",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "لزيادة", "زيادة", "زياده",
    "الإنتاجية", "الانتاجية", "الإنتاج", "الانتاج", "إنتاج", "انتاج",
    "الذكاء", "الاصطناعي", "الاصطناعيّ",
    "أدوات", "أداة", "السر", "أسرار",
    "أفضل", "أحسن",
}

ALL_STOPWORDS = STOPWORDS_EN | STOPWORDS_AR


# ══════════════════════════════════════════════════════════════════
# استخراج bigrams
# ══════════════════════════════════════════════════════════════════

def normalize_word(word: str) -> str:
    word = word.lower().strip()
    word = re.sub(r"[\u064B-\u0652]", "", word)
    word = re.sub(r"[^\w\u0600-\u06FF\s]", "", word)
    return word.strip()


def extract_bigrams(title: str) -> list[str]:
    if not title:
        return []
    tokens = re.split(r"[\s\-_|:,.!?()\[\]{}\"'’]+", title.lower())
    tokens = [normalize_word(t) for t in tokens if t and t.strip()]
    keywords = [
        t for t in tokens
        if t and t not in ALL_STOPWORDS and len(t) > 2
    ]
    if len(keywords) < 2:
        return []
    return [f"{keywords[i]} {keywords[i+1]}" for i in range(len(keywords) - 1)]


def canonical_bigram(bigram: str) -> str:
    return bigram.lower().strip()


# ══════════════════════════════════════════════════════════════════
# البيانات المُجمَّعة — 3 استعلامات بدل N+1
# ══════════════════════════════════════════════════════════════════

def _load_bulk_data(db: Session, limit: int):
    """
    يُحمّل كل البيانات المطلوبة في 3 استعلامات بدل 2260.

    Returns:
        videos: list[YouTubeVideo]
        latest_snaps: dict[video_id -> VideoSnapshot]
        earliest_snaps: dict[video_id -> VideoSnapshot]
        channels: dict[channel_id -> YouTubeChannel]
    """
    # 1. اجلب الفيديوهات
    videos = (
        db.query(YouTubeVideo)
        .order_by(YouTubeVideo.created_at.desc())
        .limit(limit)
        .all()
    )
    if not videos:
        return [], {}, {}, {}

    video_ids = [v.id for v in videos]
    channel_ids = list({v.channel_id for v in videos if v.channel_id})

    # 2. احسب min/max captured_at لكل فيديو (استعلام واحد)
    snap_min_max = (
        db.query(
            VideoSnapshot.video_id,
            func.min(VideoSnapshot.captured_at).label("first_at"),
            func.max(VideoSnapshot.captured_at).label("last_at"),
        )
        .filter(VideoSnapshot.video_id.in_(video_ids))
        .group_by(VideoSnapshot.video_id)
        .all()
    )
    time_map = {row.video_id: (row.first_at, row.last_at) for row in snap_min_max}

    # 3. اجلب الـsnapshots الفعلية لأول وآخر وقت (استعلام واحد)
    first_times = {t[0] for t in time_map.values() if t[0]}
    last_times = {t[1] for t in time_map.values() if t[1]}
    all_times = first_times | last_times

    latest_snaps: dict[int, VideoSnapshot] = {}
    earliest_snaps: dict[int, VideoSnapshot] = {}

    if all_times:
        snaps = (
            db.query(VideoSnapshot)
            .filter(VideoSnapshot.video_id.in_(video_ids))
            .filter(VideoSnapshot.captured_at.in_(all_times))
            .all()
        )
        for snap in snaps:
            vid = snap.video_id
            first_at, last_at = time_map.get(vid, (None, None))
            if last_at and snap.captured_at == last_at:
                if vid not in latest_snaps or snap.captured_at > latest_snaps[vid].captured_at:
                    latest_snaps[vid] = snap
            if first_at and snap.captured_at == first_at:
                if vid not in earliest_snaps or snap.captured_at < earliest_snaps[vid].captured_at:
                    earliest_snaps[vid] = snap

    # 4. اجلب القنوات (استعلام واحد)
    channels: dict[int, YouTubeChannel] = {}
    if channel_ids:
        ch_rows = (
            db.query(YouTubeChannel)
            .filter(YouTubeChannel.id.in_(channel_ids))
            .all()
        )
        channels = {c.id: c for c in ch_rows}

    return videos, latest_snaps, earliest_snaps, channels


# ══════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ══════════════════════════════════════════════════════════════════

def extract_topics(
    db: Session,
    limit: int = 500,
    min_videos: int = 2,
) -> list[dict]:
    """
    النسخة المحسّنة: 3 استعلامات بدل N+1.
    """
    videos, latest_snaps, earliest_snaps, channels = _load_bulk_data(db, limit)
    if not videos:
        return []

    # ابنِ video_data
    video_data = []
    for v in videos:
        bigrams = extract_bigrams(v.title or "")
        if not bigrams:
            continue

        latest = latest_snaps.get(v.id)
        if not latest:
            continue

        # velocity
        earliest = earliest_snaps.get(v.id)
        velocity = None
        if earliest and earliest.id != latest.id:
            hours = (latest.captured_at - earliest.captured_at).total_seconds() / 3600
            if hours >= 0.5:
                velocity = (latest.view_count - earliest.view_count) / hours

        # channel
        ch = channels.get(v.channel_id)
        subs = ch.subscriber_count if ch else 0

        breakout = None
        if subs and subs > 0:
            breakout = latest.view_count / subs

        engagement = None
        if latest.view_count > 0:
            engagement = (latest.like_count + latest.comment_count) / latest.view_count

        video_data.append({
            "video": v,
            "bigrams": bigrams,
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

    # تجميع
    clusters: dict[str, list] = defaultdict(list)
    for item in video_data:
        for bg in item["bigrams"]:
            clusters[canonical_bigram(bg)].append(item)

    topics = []
    for bigram, items in clusters.items():
        if len(items) < min_videos:
            continue

        seen = set()
        unique_items = []
        for it in items:
            vid = it["video"].id
            if vid not in seen:
                seen.add(vid)
                unique_items.append(it)
        items = unique_items

        if len(items) < min_videos:
            continue

        views_list = [it["views"] for it in items if it["views"]]
        velocity_list = [it["velocity"] for it in items if it["velocity"] is not None]
        breakout_list = [it["breakout"] for it in items if it["breakout"] is not None]
        engagement_list = [it["engagement"] for it in items if it["engagement"] is not None]
        unique_channels = {it["channel_id"] for it in items}
        unique_channel_sizes = [it["channel_subs"] for it in items if it["channel_subs"]]

        pub_dates = [it["published_at"] for it in items if it["published_at"]]
        latest_published = max(pub_dates) if pub_dates else None
        days_since_latest = None
        if latest_published:
            days_since_latest = (datetime.utcnow() - latest_published).days

        sorted_items = sorted(items, key=lambda x: x["views"] or 0, reverse=True)
        sample_titles = [it["video"].title for it in sorted_items[:5]]

        co_bigrams = Counter()
        for it in items:
            for bg in it["bigrams"]:
                cbg = canonical_bigram(bg)
                if cbg != bigram:
                    co_bigrams[cbg] += 1

        topics.append({
            "topic": bigram,
            "topic_display": bigram.title(),
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
            "co_keywords": [k for k, _ in co_bigrams.most_common(5)],
        })

    topics.sort(key=lambda t: t["videos_count"], reverse=True)
    return topics


def get_topic_detail(db: Session, topic_name: str) -> Optional[dict]:
    topic_name_lower = topic_name.lower().strip()
    all_topics = extract_topics(db, limit=1000, min_videos=2)
    topic = next((t for t in all_topics if t["topic"] == topic_name_lower), None)
    if not topic:
        return None

    words = topic_name_lower.split()
    if len(words) >= 2:
        from sqlalchemy import and_
        videos = (
            db.query(YouTubeVideo)
            .filter(and_(
                YouTubeVideo.title.ilike(f"%{words[0]}%"),
                YouTubeVideo.title.ilike(f"%{words[1]}%"),
            ))
            .order_by(YouTubeVideo.published_at.desc())
            .limit(20)
            .all()
        )
    else:
        videos = (
            db.query(YouTubeVideo)
            .filter(YouTubeVideo.title.ilike(f"%{topic_name_lower}%"))
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
