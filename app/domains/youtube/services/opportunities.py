"""
Opportunity Engine — يربط topics + scoring، ويرتب الفرص.

النسخة 3:
  • dedupe أسرع بـ O(n) بدل O(n²) باستخدام فهرس words
  • دمج الـbigrams المتشابهة (التي تشترك في كلمة معنوية)
  • استثناء الكلمات العامة جدًا من الدمج
  • limit=500 بدل 1000 لتسريع الاستعلام
"""
from collections import defaultdict
from typing import Optional

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
    دمج الـbigrams المتشابهة — نسخة O(n) بدل O(n²).

    الخوارزمية:
      1. رتّب حسب videos_count تنازليًا
      2. ابنِ فهرس: word → [topic_indices]
      3. لكل topic، ابحث عن التوأم عبر الفهرس
      4. ادمج في مجموعة واحدة
    """
    if not topics:
        return topics

    sorted_topics = sorted(topics, key=lambda t: t["videos_count"], reverse=True)

    # ─── فهرس: word → list of topic indices ─────────────────────
    # نستخدم الكلمات المعنوية فقط (بدون GENERIC_WORDS)
    word_index: dict[str, list[int]] = defaultdict(list)
    for idx, t in enumerate(sorted_topics):
        sig_words = _significant_words(t["topic"])
        for w in sig_words:
            word_index[w].append(idx)
    # ─────────────────────────────────────────────────────────────

    merged: list[dict] = []
    used: set[int] = set()

    for i, t in enumerate(sorted_topics):
        if i in used:
            continue

        canonical = t
        canonical_words = _significant_words(t["topic"])

        if not canonical_words:
            # لا توجد كلمات معنوية — احتفظ به كما هو
            merged.append(t)
            used.add(i)
            continue

        # ─── ابحث عن bigrams متشابهة بسرعة O(1) لكل كلمة ─────────
        related_indices: set[int] = set()
        for w in canonical_words:
            for j in word_index.get(w, []):
                if j == i or j in used:
                    continue
                # تأكد أن التشابه ليس فقط في كلمة واحدة عامة
                other_words = _significant_words(sorted_topics[j]["topic"])
                if canonical_words & other_words:
                    related_indices.add(j)
        # ─────────────────────────────────────────────────────────

        used.add(i)
        for j in related_indices:
            used.add(j)

        # اجمع معلومات
        related_topics_list = [sorted_topics[j] for j in related_indices]
        variants = [rt["topic"] for rt in related_topics_list]

        # ادمج sample_titles (بحد أقصى 5)
        all_titles = list(canonical.get("sample_titles", []))
        for rt in related_topics_list:
            for title in rt.get("sample_titles", []):
                if title not in all_titles and len(all_titles) < 5:
                    all_titles.append(title)

        # اجمع co_keywords
        all_co = list(canonical.get("co_keywords", []))
        for rt in related_topics_list:
            for ck in rt.get("co_keywords", []):
                if ck not in all_co:
                    all_co.append(ck)

        merged_topic = {
            **canonical,
            "topic": canonical["topic"],   # الاحتفاظ بالـbigram الأكبر
            "variants": variants,          # قائمة الـbigrams المدمجة
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
    1. يستدعي extract_topics (النسخة 3 المحسّنة)
    2. يدمج المتشابهة (dedupe)
    3. يحسب opportunity لكل topic
    4. يفلتر ويرتب
    """
    # ⚠️ limit=500 (بدل 1000) لتسريع الاستعلام الأولي
    topics = extract_topics(db, limit=500, min_videos=min_videos)
    if not topics:
        return []

    if dedupe:
        topics = _dedupe_topics(topics)

    scored = [compute_opportunity(t, topics) for t in topics]

    filtered = [
        o for o in scored
        if o["demand"] >= min_demand and o["competition"] <= max_competition
    ]

    filtered.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return filtered[:limit]


def get_top_opportunity(db: Session) -> Optional[dict]:
    """يرجع أعلى فرصة واحدة."""
    opps = get_opportunities(db, limit=1)
    return opps[0] if opps else None
