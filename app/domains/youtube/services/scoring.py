"""
Opportunity Scoring — حساب نقاط الفرصة لكل topic.

لا يستدعي DB ولا API. يعمل على dicts فقط.
"""
from datetime import datetime
from typing import Optional


# ══════════════════════════════════════════════════════════════════
# تطبيع القيم إلى 0-100
# ══════════════════════════════════════════════════════════════════

def normalize(value: float, min_val: float, max_val: float) -> float:
    """يطبّع قيمة إلى مدى 0-100."""
    if max_val <= min_val:
        return 50.0
    pct = (value - min_val) / (max_val - min_val)
    return round(max(0.0, min(100.0, pct * 100)), 2)


def _min_max(values: list[float]) -> tuple[float, float]:
    """يرجع (min, max) لقائمة قيم. لو فارغة، يرجع (0, 1)."""
    if not values:
        return 0.0, 1.0
    return min(values), max(values)


# ══════════════════════════════════════════════════════════════════
# المكونات الأساسية
# ══════════════════════════════════════════════════════════════════

def compute_demand_score(topic: dict, all_topics: list[dict]) -> float:
    """
    الطلب = مزيج من:
    - median_views (لكل الفيديوهات في الموضوع)
    - avg_engagement (جودة التفاعل)
    """
    all_views = [t["median_views"] for t in all_topics if t["median_views"] > 0]
    all_eng = [t["avg_engagement"] for t in all_topics if t["avg_engagement"] > 0]

    v_min, v_max = _min_max(all_views)
    e_min, e_max = _min_max(all_eng)

    views_score = normalize(topic["median_views"], v_min, v_max)
    eng_score = normalize(topic["avg_engagement"], e_min, e_max)

    return round(0.7 * views_score + 0.3 * eng_score, 2)


def compute_velocity_score(topic: dict, all_topics: list[dict]) -> float:
    """السرعة = متوسط views/hour مقارنة ببقية المواضيع."""
    all_v = [t["avg_velocity"] for t in all_topics if t["avg_velocity"] > 0]
    v_min, v_max = _min_max(all_v)
    return normalize(topic["avg_velocity"], v_min, v_max)


def compute_freshness_score(topic: dict) -> float:
    """
    الحداثة = كم يوم مر على آخر فيديو ناجح.
    - 0 أيام → 100
    - 30 يوم → 50
    - 90 يوم → 0
    """
    days = topic.get("days_since_latest")
    if days is None:
        return 30.0
    if days <= 0:
        return 100.0
    if days >= 90:
        return 0.0
    return round(100 * (1 - days / 90), 2)


def compute_competition_score(topic: dict, all_topics: list[dict]) -> float:
    """
    المنافسة = 0-100 حيث:
    - 0 = منافسة عالية جدًا (سيئ)
    - 100 = منافسة منخفضة جدًا (جيد)

    تعتمد على:
    - عدد الفيديوهات (كلما زاد، زادت المنافسة)
    - متوسط حجم القنوات (كلما كبرت، صعب أكثر)
    """
    all_counts = [t["videos_count"] for t in all_topics]
    all_sizes = [t["avg_channel_size"] for t in all_topics if t["avg_channel_size"] > 0]

    c_min, c_max = _min_max(all_counts)
    s_min, s_max = _min_max(all_sizes)

    # عدد الفيديوهات: معكوس (كلما زاد، قلت النتيجة)
    count_score = 100 - normalize(topic["videos_count"], c_min, c_max)
    # حجم القنوات: معكوس
    size_score = 100 - normalize(topic["avg_channel_size"], s_min, s_max)

    return round(0.6 * count_score + 0.4 * size_score, 2)


def compute_breakout_score(topic: dict, all_topics: list[dict]) -> float:
    """
    الاختراق = متوسط views/subscribers.
    كلما زاد، زادت فرصة نجاح قنوات صغيرة.
    """
    all_b = [t["avg_breakout"] for t in all_topics if t["avg_breakout"] > 0]
    if not all_b:
        return 50.0
    b_min, b_max = _min_max(all_b)
    return normalize(topic["avg_breakout"], b_min, b_max)


# ══════════════════════════════════════════════════════════════════
# الدالة الرئيسية
# ══════════════════════════════════════════════════════════════════

WEIGHTS = {
    "demand":      0.30,
    "velocity":    0.20,
    "freshness":   0.15,
    "competition": 0.20,
    "breakout":    0.15,
}


def compute_opportunity(topic: dict, all_topics: list[dict]) -> dict:
    """
    يحسب Opportunity Score + كل المكونات + تفسيرات.
    """
    demand = compute_demand_score(topic, all_topics)
    velocity = compute_velocity_score(topic, all_topics)
    freshness = compute_freshness_score(topic)
    competition = compute_competition_score(topic, all_topics)
    breakout = compute_breakout_score(topic, all_topics)

    opportunity = (
        WEIGHTS["demand"] * demand
        + WEIGHTS["velocity"] * velocity
        + WEIGHTS["freshness"] * freshness
        + WEIGHTS["competition"] * competition
        + WEIGHTS["breakout"] * breakout
    )

    # ═══ لماذا الآن؟ ═══
    why_now = []
    if velocity > 70:
        why_now.append(f"سرعة نمو عالية ({int(topic['avg_velocity'])} مشاهدة/ساعة)")
    if breakout > 70:
        why_now.append(f"قنوات صغيرة تخترق ({int(topic['avg_channel_size'])} مشترك متوسط)")
    if competition < 40:
        why_now.append(f"منافسة منخفضة ({topic['videos_count']} فيديو فقط)")
    if freshness > 80:
        why_now.append(f"محتوى حديث ({topic.get('days_since_latest')} يوم)")
    if topic["channels_count"] >= 4:
        why_now.append(f"تنوّع قنوات ({topic['channels_count']} قناة)")
    if not why_now:
        why_now.append("إشارات متوسطة — يستحق المتابعة")

    return {
        **topic,
        "opportunity_score": round(opportunity, 2),
        "demand": demand,
        "velocity": velocity,
        "freshness": freshness,
        "competition": competition,
        "breakout": breakout,
        "why_now": why_now,
    }
