"""
Topic Aggregation — تجميع العناوين المتشابهة في Topics.

النسخة 2:
  • bigrams فقط (بدل كلمات مفردة) لدقة أعلى
  • stopwords عربية موسّعة
  • تطبيع bigrams لمنع التكرار
  • min_videos افتراضي = 2

يعمل على البيانات المخزَّنة فقط (لا يستدعي YouTube API).
"""
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.domains.youtube.models import YouTubeVideo, YouTubeChannel, VideoSnapshot


# ══════════════════════════════════════════════════════════════════
# Stopwords
# ══════════════════════════════════════════════════════════════════

STOPWORDS_EN = {
    # Articles / prepositions
    "a", "an", "the", "and", "or", "but", "if", "then", "else",
    "of", "to", "in", "on", "at", "by", "for", "with", "about",
    "from", "into", "through", "during", "before", "after",
    "over", "under", "between", "without", "within",
    # Verbs
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "should", "could", "can", "may", "might",
    "get", "got", "make", "made", "use", "used", "using",
    "learn", "learning", "watch", "watching", "see", "saw",
    "know", "knew", "want", "wanted", "need", "needed",
    # Pronouns
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "there",
    # Question words
    "what", "which", "who", "when", "where", "why", "how",
    # Quantifiers
    "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very",
    # Common
    "just", "now", "here", "up", "down", "out", "off",
    "vs", "via", "per", "new", "old",
    "best", "top", "full", "free", "pro", "vs.",
    "2024", "2025", "2026", "2027",
    # Content-generic
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
    "here", "there", "everywhere",
    "top 5", "top 10", "top 3",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
}

STOPWORDS_AR = {
    # حروف جر
    "في", "من", "إلى", "على", "عن", "مع", "حتى", "منذ", "خلال",
    "بين", "أمام", "خلف", "فوق", "تحت", "حول", "ضد", "حسب",
    "عبر", "نحو", "لدى", "إلى", "بعد", "قبل",
    # ضمائر
    "هو", "هي", "هم", "هن", "أنا", "أنت", "نحن", "إياه", "إياها",
    "هذا", "هذه", "ذلك", "تلك", "هؤلاء", "أولئك",
    "التي", "الذي", "الذين", "اللاتي",
    # أدوات استفهام
    "ما", "ماذا", "كيف", "لماذا", "متى", "أين", "هل",
    # أدوات ربط
    "ثم", "أو", "و", "لكن", "بل", "قد", "كان", "كانت",
    "يكون", "تكون", "ليس", "ليست",
    "إن", "أن", "إذا", "لو", "لولا",
    "لا", "لم", "لن", "ما",
    # كميات
    "كل", "بعض", "أي", "جميع", "معظم", "كثير", "قليل",
    # كلمات شائعة ضعيفة
    "الأول", "الأخير", "الجديد", "القديم", "أفضل", "أكبر", "أصغر",
    "شرح", "درس", "دورة", "كورس", "مقدمة", "طريقة", "طرق",
    "خطوات", "نصائح", "حيل", "أسرار",
    "كامل", "كاملة", "شامل", "بسيط", "سهل", "سريع",
    "الحلقة", "الجزء", "فيديو", "شورت", "تحديث", "أخبار",
    # أرقام
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    # كلمات رأيتها في النتائج السابقة
    "لزيادة", "زيادة", "زياده",
    "الإنتاجية", "الانتاجية", "الإنتاج", "الانتاج", "إنتاج", "انتاج",
    "الذكاء", "الاصطناعي", "الاصطناعيّ",
    "أدوات", "أداة", "السر", "أسرار",
    "أفضل", "أحسن",
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
    # إزالة الرموز (نُبقي الحروف والمسافات)
    word = re.sub(r"[^\w\u0600-\u06FF\s]", "", word)
    return word.strip()


def extract_bigrams(title: str) -> list[str]:
    """
    يستخرج bigrams (كلمتين متتاليتين) من عنوان.
    يطبّع كل كلمة، يحذف stopwords، ثم يبني bigrams.

    يرجع قائمة bigrams مثل: ["voice cloning", "cloning tutorial", ...]
    """
    if not title:
        return []

    # تقسيم على المسافات والرموز
    tokens = re.split(r"[\s\-_|:,.!?()\[\]{}\"'’]+", title.lower())
    tokens = [normalize_word(t) for t in tokens if t and t.strip()]

    # فلترة stopwords والكلمات القصيرة
    keywords = [
        t for t in tokens
        if t and t not in ALL_STOPWORDS and len(t) > 2
    ]

    if len(keywords) < 2:
        return []

    # bigrams
    bigrams = []
    for i in range(len(keywords) - 1):
        bigram = f"{keywords[i]} {keywords[i+1]}"
        bigrams.append(bigram)

    return bigrams


def canonical_bigram(bigram: str) -> str:
    """
    يوحّد الـbigram: يرتب الكلمتين أبجديًا لمنع التكرار.
    مثال: "cloning voice" و "voice cloning" → "cloning voice"

    لكن هذا قد يفسد المعنى. لذا نكتفي بـlowercase وstrip.
    """
    return bigram.lower().strip()


# ══════════════════════════════════════════════════════════════════
# Snapshot helpers
# ══════════════════════════════════════════════════════════════════

def _get_latest_snapshot(db: Session, video_id: int) -> Optional[VideoSnapshot]:
    return (
        db.query(VideoSnapshot)
        .filter_by(video_id=video_id)
        .order_by(VideoSnapshot.captured_at.desc())
        .first()
    )


def _get_earliest_snapshot(db: Session, video_id: int) -> Optional[VideoSnapshot]:
    return (
        db.query(VideoSnapshot)
        .filter_by(video_id=video_id)
        .order_by(VideoSnapshot.captured_at.asc())
        .first()
    )


def _compute_video_velocity(db: Session, video_id: int) -> Optional[float]:
    """يحسب views_per_hour من أول وآخر snapshot."""
    first = _get_earliest_snapshot(db, video_id)
    last = _get_latest_snapshot(db, video_id)
    if not first or not last or first.id == last.id:
        return None

    hours = (last.captured_at - first.captured_at).total_seconds() / 3600
    if hours < 0.5:
        return None

    return (last.view_count - first.view_count) / hours


# ══════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ══════════════════════════════════════════════════════════════════

def extract_topics(
    db: Session,
    limit: int = 500,
    min_videos: int = 2,
) -> list[dict]:
    """
    الدالة الرئيسية.

    1. اجلب آخر limit فيديو
    2. استخرج bigrams من كل عنوان
    3. جمّع الفيديوهات حسب bigram مشترك
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

    # 2. احسب بيانات كل فيديو مرة واحدة
    video_data = []
    for v in videos:
        bigrams = extract_bigrams(v.title or "")
        if not bigrams:
            continue

        latest = _get_latest_snapshot(db, v.id)
        if not latest:
            continue

        velocity = _compute_video_velocity(db, v.id)
        subs = v.channel.subscriber_count if v.channel else 0

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

    # 3. التجميع — كل bigram يصبح cluster
    clusters: dict[str, list] = defaultdict(list)
    for item in video_data:
        for bg in item["bigrams"]:
            clusters[canonical_bigram(bg)].append(item)

    # 4. احسب إحصائيات لكل cluster
    topics = []
    for bigram, items in clusters.items():
        if len(items) < min_videos:
            continue

        # تجنّب تكرار نفس الفيديو في cluster واحد
        # (لو نفس الفيديو فيه نفس الـbigram مرتين — نادر لكن ممكن)
        seen_video_ids = set()
        unique_items = []
        for it in items:
            vid = it["video"].id
            if vid not in seen_video_ids:
                seen_video_ids.add(vid)
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

        # كلمات مصاحبة
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

    # 5. رتّب حسب عدد الفيديوهات
    topics.sort(key=lambda t: t["videos_count"], reverse=True)
    return topics


def get_topic_detail(db: Session, topic_name: str) -> Optional[dict]:
    """
    تفاصيل topic معين + الفيديوهات المرتبطة به.
    topic_name الآن هو bigram، مثل "voice cloning".
    """
    topic_name_lower = topic_name.lower().strip()

    all_topics = extract_topics(db, limit=1000, min_videos=2)
    topic = next(
        (t for t in all_topics if t["topic"] == topic_name_lower),
        None,
    )
    if not topic:
        return None

    # اجلب الفيديوهات التي تحتوي على الـbigram في العنوان
    # (بحث بسيط — يمكن تحسينه لاحقًا)
    words = topic_name_lower.split()
    if len(words) >= 2:
        # ابحث عن العناوين التي تحتوي كلتا الكلمتين
        from sqlalchemy import and_
        videos = (
            db.query(YouTubeVideo)
            .filter(
                and_(
                    YouTubeVideo.title.ilike(f"%{words[0]}%"),
                    YouTubeVideo.title.ilike(f"%{words[1]}%"),
                )
            )
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
