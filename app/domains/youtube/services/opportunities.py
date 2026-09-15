"""
Opportunity Engine — يربط topics + scoring، ويرتب الفرص.

النسخة 2:
  • دمج الـbigrams المتشابهة (التي تشترك في كلمة معنوية)
  • استثناء الكلمات العامة جدًا (مثل "ai") من الدمج
"""
from sqlalchemy.orm import Session

from app.domains.youtube.services.topics import extract_topics
from app.domains.youtube.services.scoring import compute_opportunity


# كلمات عامة جدًا — لا تُستخدم للدمج لأنها تجمع كل شيء
GENERIC_WORDS = {
    "ai", "the", "and", "for", "with", "from",
    "how", "what", "why", "when", "where",
    "2024", "2025", "2026", "2027",
    # عربية
    "في", "من", "إلى", "على", "عن", "مع",
    "الذكاء", "الاصطناعي",
}


def _significant_words(bigram: str) -> set[str]:
    """يرجع الكلمات المعنوية (بدون generic) في bigram."""
    words = set(bigram.lower().split())
    return words - GENERIC_WORDS


def _dedupe_topics(topics: list[dict]) -> list[dict]:
    """
    دمج الـbigrams المتشابهة.

    الخوارزمية:
      1. رتّب حسب videos_count تنازليًا
      2. ابدأ من الأكبر
      3. لأي topic أصغر يشترك في كلمة معنوية → ادمجه
      4. المعنوية = كلمة ليست في GENERIC_WORDS
    """
    if not topics:
        return topics

    sorted_topics = sorted(topics, key=lambda t: t["videos_count"], reverse=True)

    merged: list[dict] = []
    used = set()

    for i, t in enumerate(sorted_topics):
        if i in used:
            continue

        canonical = t
        canonical_words = _significant_words(t["topic"])
        if not canonical_words:
            # لا توجد كلمات معنوية — احتفظ به كما هو
            merged.append(t)
            continue

        # ابحث عن bigrams متشابهة
        related_indices = []
        for j, other in enumerate(sorted_topics):
            if j == i or j in used:
                continue
            other_words = _significant_words(other["topic"])
            if not other_words:
                continue
            # تشترك في كلمة معنوية واحدة على الأقل
            if canonical_words & other_words:
                related_indices.append(j)

        # سجّل الكل كـused
        used.add(i)
        for j in related_indices:
            used.add(j)

        # اجمع معلومات الـbigrams المرتبطة
        related_topics = [sorted_topics[j] for j in related_indices]
        co_keywords_extra = [rt["topic"] for rt in related_topics]

        # ادمج sample_titles (بحد أقصى 5)
        all_titles = list(canonical.get("sample_titles", []))
        for rt in related_topics:
            for title in rt.get("sample_titles", []):
                if title not in all_titles and len(all_titles) < 5:
                    all_titles.append(title)

        # اجمع co_keywords
        all_co = list(canonical.get("co_keywords", []))
        for rt in related_topics:
            for ck in rt.get("co_keywords", []):
                if ck not in all_co:
                    all_co.append(ck)

        merged_topic = {
            **canonical,
            "topic": canonical["topic"],  # الاحتفاظ بالـbigram الأكبر
            "variants": co_keywords_extra,  # قائمة الـbigrams المدمجة
            "sample_titles": all_titles[:5],
            "co_keywords": all_co[:8],
        }
        merged.append(merged_topic)

    return merged


def get_opportunities(
    db: Session,
    limit: int = 50,
    min_videos: int = 2,
    min_demand: float = 0.0,
    max_competition: float = 100.0,
    dedupe: bool = True,
) -> list[dict]:
    """
    1. يستدعي extract_topics
    2. يحسب opportunity لكل topic
    3. (اختياري) يدمج المتشابهة
    4. يفلتر
    5. يرتب تنازليًا
    """
    topics = extract_topics(db, limit=1000, min_videos=min_videos)
    if not topics:
        return []

    # دمج قبل الحساب (لأن الدمج يغيّر videos_count وما شابه)
    if dedupe:
        topics = _dedupe_topics(topics)

    scored = [compute_opportunity(t, topics) for t in topics]

    filtered = [
        o for o in scored
        if o["demand"] >= min_demand and o["competition"] <= max_competition
    ]

    filtered.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return filtered[:limit]


def get_top_opportunity(db: Session) -> dict | None:
    opps = get_opportunities(db, limit=1)
    return opps[0] if opps else None
