"""
Deep Market Intelligence Engine for Telegram messages.
Pure Python — no external AI/ML dependencies required.
Produces actionable market opportunities, gaps, and demand signals.
"""
import re
import math
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any

# ─── Arabic + English stop words ─────────────────────────────────────────────

STOP_WORDS = {
    "في","من","على","إلى","عن","مع","هذا","هذه","ذلك","تلك","هو","هي","هم","هن",
    "أنا","أنت","نحن","كان","كانت","كانوا","يكون","تكون","أن","إن","لا","ما","لم",
    "لن","قد","وقد","كل","بعض","أو","إما","حتى","بعد","قبل","عند","منذ","خلال",
    "وهو","وهي","وهم","وهن","وأن","وإن","أي","أية","فقط","هناك","هنا","ثم","بين",
    "حول","عبر","نحو","مثل","غير","كما","لكن","بل","إلا","سوى","ولا","ولم","ولن",
    "أيضا","كذلك","بذلك","لذا","لذلك","لأن","لأنه","لأنها","إذا","إذ","حين","عندما",
    "الذي","التي","الذين","اللواتي","اللاتي","الان","الآن","اليوم","ماذا","كيف","لماذا",
    "متى","أين","الله","شكرا","شكراً","يعني","تمام","حسنا","حسناً","صح","صحيح",
    "ايوه","ايه","طيب","بس","زي","عشان","علشان","اللي","اللى","ده","دي","دا",
    "a","the","is","are","was","were","be","been","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","and","or","but",
    "not","this","that","these","those","it","its","they","them","their","we","us",
    "our","you","your","he","she","him","her","his","i","me","my","an","in","on",
    "at","to","of","for","with","by","from","up","about","into","through","then",
    "just","so","if","as","out","can","get","one","all","more","also","than","its",
}

# ─── Market Signal Keyword Banks ──────────────────────────────────────────────

OPPORTUNITY_PATTERNS: Dict[str, Dict] = {
    "طلب_منتج": {
        "label": "🎯 طلبات منتج/خدمة مباشرة",
        "keywords": ["أريد","أبغى","أبحث","محتاج","محتاجة","ابغى","أحتاج","ممكن توفر",
                     "need","want","looking for","searching","where can i"],
        "action": "الرد الفوري على طلبات العملاء وتحويلها إلى صفقات",
        "weight": 10,
    },
    "استفسار_سعر": {
        "label": "💰 استفسارات الأسعار",
        "keywords": ["كم سعر","كم ثمن","كم تكلفة","سعر","ثمن","بكم","تكلفة",
                     "price","cost","how much","pricing","fee","rate","quote"],
        "action": "توضيح هيكل الأسعار وتقديم عروض قيمة مباشرة",
        "weight": 12,
    },
    "مقارنة_منافس": {
        "label": "🆚 مقارنات بالمنافسين",
        "keywords": ["مقارنة","أفضل من","أحسن","بديل","بدلاً من","غيره","بدل",
                     "versus","vs","compare","better than","alternative","instead"],
        "action": "تطوير نقاط التميز والرد الاستراتيجي على المقارنات",
        "weight": 14,
    },
    "فرصة_شراكة": {
        "label": "🤝 فرص شراكة وتوزيع",
        "keywords": ["تعاون","شراكة","توزيع","وكالة","عمولة","وكيل","تجار",
                     "partner","partnership","collaborate","distribute","commission","wholesale","reseller"],
        "action": "التواصل المباشر مع المهتمين وبناء شبكة توزيع",
        "weight": 18,
    },
    "طلب_ميزة": {
        "label": "✨ طلبات تطوير وميزات",
        "keywords": ["ممكن تضيف","هل يدعم","لو كان فيه","أتمنى","نتمنى","لو يوجد",
                     "can you add","does it support","wish","feature request","would be nice"],
        "action": "إدراج الطلبات في خارطة التطوير وإبلاغ العملاء بالتحديثات",
        "weight": 8,
    },
    "مخاوف_جودة": {
        "label": "🔍 مخاوف الجودة والأصالة",
        "keywords": ["جودة","ضمان","أصلي","مغشوش","اصل","تقليد","مزور",
                     "quality","guarantee","original","authentic","warranty","fake","counterfeit"],
        "action": "تعزيز ضمانات الجودة والشهادات لبناء الثقة",
        "weight": 11,
    },
    "خدمة_عملاء": {
        "label": "📞 طلبات خدمة العملاء",
        "keywords": ["مساعدة","دعم","تواصل","تواصلوا","كلموني","رقم","واتساب",
                     "help","support","contact","reach out","phone","customer service"],
        "action": "تحسين قنوات الدعم وسرعة الاستجابة",
        "weight": 9,
    },
}

GAP_DEFINITIONS: Dict[str, Dict] = {
    "أسئلة_متكررة": {
        "label": "❓ أسئلة متكررة بلا إجابات",
        "keywords": ["؟","?","كيف","ماذا","هل","لماذا","متى","أين","من أين","ما هو"],
        "opportunity": "تحويل هذه الأسئلة لمحتوى تسويقي وصفحات FAQ تجذب العملاء",
        "weight": 8,
    },
    "شكاوى_متكررة": {
        "label": "⚠️ نقاط ألم متكررة",
        "keywords": ["مشكلة","خطأ","لا يعمل","معطل","سيء","رديء","ضعيف","بطيء",
                     "problem","issue","error","not working","broken","slow","bad"],
        "opportunity": "معالجة هذه المشاكل يفتح فرص تميّز واضح على المنافسين",
        "weight": 14,
    },
    "حساسية_السعر": {
        "label": "💸 حساسية السعر — فرصة تسعير",
        "keywords": ["غالي","باهظ","مو مناسب","مش مناسب","كثير","ما يستاهل",
                     "expensive","overpriced","too much","not worth","costly"],
        "opportunity": "تقديم حزم مرنة وعروض قيمة تناسب شرائح مختلفة",
        "weight": 13,
    },
    "نقص_معلومات": {
        "label": "📚 نقص في المعلومات والمحتوى",
        "keywords": ["لا أعرف","ما أعرف","لا أجد","ما وجدت","ما لقيت","ما أدري",
                     "don't know","can't find","not sure","unclear","confused"],
        "opportunity": "إنتاج محتوى تعليمي وتسويقي يُعالج هذا الغموض",
        "weight": 7,
    },
    "تأخر_التسليم": {
        "label": "🚚 مشاكل التسليم والانتظار",
        "keywords": ["متى","انتظر","تأخر","وصل","يصل","شحن","توصيل",
                     "when","waiting","delayed","shipping","delivery","tracking"],
        "opportunity": "تحسين الشفافية في عمليات التسليم وتقديم تتبع لحظي",
        "weight": 10,
    },
}

DEMAND_SIGNALS: Dict[str, List[str]] = {
    "طلب_شراء_فوري": ["اشتري","أشتري","أريد أشتري","ابغى اشتري","buy","purchase","order now"],
    "طلب_كميات": ["كميات","جملة","wholesale","bulk","quantity","كمية كبيرة"],
    "طلب_عينة": ["نموذج","عينة","تجربة","sample","trial","test","demo"],
    "مقارنة_جدية": ["هذا أفضل","اختار","أنصحك","recommend","best option","better"],
}


# ─── Text Utilities ───────────────────────────────────────────────────────────

def clean(text: str) -> str:
    text = re.sub(r'http\S+|www\S+|@\S+|#\S+', ' ', text or "")
    text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)
    text = re.sub(r'\d+', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def tokenize(text: str) -> List[str]:
    return [t for t in clean(text).lower().split() if len(t) >= 3 and t not in STOP_WORDS]


def tfidf_scores(messages: List[str]) -> Dict[str, float]:
    """Return term → TF-IDF score across all documents."""
    docs = [tokenize(d) for d in messages]
    N = len(docs) or 1
    df: Counter = Counter()
    for d in docs:
        df.update(set(d))
    tf_all: Counter = Counter()
    for d in docs:
        tf_all.update(d)
    scored = {}
    for term, cnt in tf_all.items():
        idf = math.log((N + 1) / (df[term] + 1)) + 1
        scored[term] = cnt * idf
    return scored


# ─── Analysis Modules ─────────────────────────────────────────────────────────

def extract_topics(messages: List[Dict]) -> List[Dict]:
    texts = [m.get("content", "") or "" for m in messages]
    if not texts:
        return []
    scores = tfidf_scores(texts)
    top_terms = sorted(scores.items(), key=lambda x: -x[1])[:30]

    topics = []
    used = set()
    for term, score in top_terms:
        if term in used:
            continue
        related = [m for m in messages if term in (m.get("content", "") or "").lower()]
        if not related:
            continue

        # Co-occurring terms
        co: Counter = Counter()
        for m in related:
            for t in tokenize(m.get("content", "")):
                if t != term and t not in used:
                    co[t] += 1
        co_terms = [t for t, _ in co.most_common(4)]

        # Sentiment breakdown for this topic
        sentiments: Counter = Counter()
        for m in related:
            ar = m.get("analysis_result") or {}
            sentiments[ar.get("sentiment", "محايد")] += 1
        dominant = sentiments.most_common(1)[0][0] if sentiments else "محايد"

        # Opportunity score: high frequency + negative sentiment = pain = opportunity
        opp_score = min(100, int(score * 2 + (20 if dominant == "سلبي" else 0)))

        topics.append({
            "term": term,
            "score": round(score, 1),
            "frequency": scores.get(term, 0),
            "message_count": len(related),
            "co_terms": co_terms,
            "dominant_sentiment": dominant,
            "opportunity_score": opp_score,
            "samples": [(m.get("content", "") or "")[:100] for m in related[:2]],
        })
        used.add(term)
        used.update(co_terms[:2])

        if len(topics) >= 12:
            break

    return topics


def detect_opportunities(messages: List[Dict]) -> List[Dict]:
    results = []
    for key, meta in OPPORTUNITY_PATTERNS.items():
        kws = meta["keywords"]
        matching = [m for m in messages
                    if any(kw.lower() in (m.get("content", "") or "").lower() for kw in kws)]
        if not matching:
            continue

        freq = len(matching)
        # Extract frequent bi-grams from matching messages
        bigrams: Counter = Counter()
        for m in matching:
            toks = tokenize(m.get("content", ""))
            for i in range(len(toks) - 1):
                bigrams[toks[i] + " " + toks[i + 1]] += 1

        chats = list({m.get("chat_title", "—") for m in matching})[:5]
        score = min(100, freq * meta["weight"])

        results.append({
            "key": key,
            "label": meta["label"],
            "frequency": freq,
            "score": score,
            "strength": "عالية 🔥" if score > 60 else "متوسطة 📊" if score > 30 else "منخفضة",
            "top_phrases": [p for p, _ in bigrams.most_common(5)],
            "active_chats": chats,
            "action": meta["action"],
            "sample": (matching[0].get("content", "") or "")[:160] if matching else "",
        })

    return sorted(results, key=lambda x: -x["score"])


def detect_gaps(messages: List[Dict]) -> List[Dict]:
    results = []
    for key, meta in GAP_DEFINITIONS.items():
        kws = meta["keywords"]
        matching = [m for m in messages
                    if any(kw.lower() in (m.get("content", "") or "").lower() for kw in kws)]
        if not matching:
            continue

        freq = len(matching)
        # Top terms inside these messages
        hot_terms: Counter = Counter()
        for m in matching:
            hot_terms.update(tokenize(m.get("content", "")))
        hot = [t for t, _ in hot_terms.most_common(6)]
        score = min(100, freq * meta["weight"])

        results.append({
            "key": key,
            "label": meta["label"],
            "frequency": freq,
            "score": score,
            "hot_topics": hot,
            "opportunity": meta["opportunity"],
            "severity": "حرج 🔴" if score > 70 else "تحذير 🟡" if score > 35 else "منخفض 🟢",
            "sample": (matching[0].get("content", "") or "")[:160] if matching else "",
        })

    return sorted(results, key=lambda x: -x["score"])


def detect_demand_signals(messages: List[Dict]) -> List[Dict]:
    results = []
    for sig_key, kws in DEMAND_SIGNALS.items():
        matching = [m for m in messages
                    if any(kw.lower() in (m.get("content", "") or "").lower() for kw in kws)]
        if not matching:
            continue

        terms: Counter = Counter()
        for m in matching:
            terms.update(tokenize(m.get("content", "")))

        labels = {
            "طلب_شراء_فوري": "🛒 نية شراء فورية",
            "طلب_كميات": "📦 طلب كميات / جملة",
            "طلب_عينة": "🧪 طلب تجربة / عينة",
            "مقارنة_جدية": "🔎 مقارنة جدية قبل الشراء",
        }

        results.append({
            "type": sig_key,
            "label": labels.get(sig_key, sig_key),
            "count": len(matching),
            "top_items": [{"term": t, "count": c} for t, c in terms.most_common(6)],
            "urgency": "عاجل" if len(matching) > 5 else "متوسط",
        })

    return results


def trend_analysis(messages: List[Dict]) -> Dict:
    if not messages:
        return {"has_data": False, "activity": [], "trending": [], "peak_day": None, "avg_daily": 0}

    by_day: Dict[str, List] = defaultdict(list)
    for m in messages:
        ra = m.get("received_at")
        try:
            day = str(ra)[:10] if ra else "unknown"
            if day != "unknown":
                by_day[day].append(m)
        except Exception:
            pass

    if not by_day:
        return {"has_data": False, "activity": [], "trending": [], "peak_day": None, "avg_daily": 0}

    days_sorted = sorted(by_day.keys())
    activity = [{"day": d, "count": len(by_day[d])} for d in days_sorted[-10:]]
    peak_day = max(by_day.items(), key=lambda x: len(x[1]))[0]
    avg_daily = round(len(messages) / max(len(by_day), 1), 1)

    # Trending: compare last 3 days vs previous
    cutoff_idx = max(0, len(days_sorted) - 3)
    recent_days = set(days_sorted[cutoff_idx:])
    older_days = set(days_sorted[:cutoff_idx])

    recent_msgs = [m for d in recent_days for m in by_day.get(d, [])]
    older_msgs = [m for d in older_days for m in by_day.get(d, [])]

    r_terms: Counter = Counter()
    o_terms: Counter = Counter()
    for m in recent_msgs:
        r_terms.update(tokenize(m.get("content", "")))
    for m in older_msgs:
        o_terms.update(tokenize(m.get("content", "")))

    trending = []
    for term, rc in r_terms.items():
        if rc < 2:
            continue
        oc = o_terms.get(term, 0) + 1
        ratio = rc / oc
        if ratio > 1.8:
            trending.append({"term": term, "recent": rc, "older": oc - 1,
                              "ratio": round(ratio, 2), "direction": "↑"})

    trending.sort(key=lambda x: -x["ratio"])

    return {
        "has_data": True,
        "activity": activity,
        "trending": trending[:8],
        "peak_day": peak_day,
        "avg_daily": avg_daily,
    }


def channel_insights(messages: List[Dict]) -> List[Dict]:
    by_chat: Dict[str, List] = defaultdict(list)
    for m in messages:
        by_chat[m.get("chat_title") or "غير معروف"].append(m)

    results = []
    for chat, msgs in sorted(by_chat.items(), key=lambda x: -len(x[1])):
        toks: Counter = Counter()
        for m in msgs:
            toks.update(tokenize(m.get("content", "")))
        sent: Counter = Counter()
        for m in msgs:
            ar = m.get("analysis_result") or {}
            sent[ar.get("sentiment", "محايد")] += 1

        # Market heat: ratio of opportunity keywords
        opp_msgs = sum(
            1 for m in msgs
            if any(kw in (m.get("content", "") or "").lower()
                   for pat in OPPORTUNITY_PATTERNS.values()
                   for kw in pat["keywords"])
        )
        heat = min(100, int(opp_msgs / max(len(msgs), 1) * 200))

        results.append({
            "chat": chat,
            "type": msgs[0].get("chat_type", "—"),
            "messages": len(msgs),
            "top_topics": [t for t, _ in toks.most_common(5)],
            "sentiment": dict(sent),
            "market_heat": heat,
            "heat_label": "حار 🔥" if heat > 60 else "متوسط 📊" if heat > 25 else "هادئ",
        })

    return results[:10]


def executive_summary(opportunities: List, gaps: List, topics: List, messages: List) -> Dict:
    total = len(messages)
    top_opp = opportunities[0]["label"] if opportunities else "—"
    top_gap = gaps[0]["label"] if gaps else "—"
    top_topic = topics[0]["term"] if topics else "—"
    opp_score = opportunities[0]["score"] if opportunities else 0
    gap_score = gaps[0]["score"] if gaps else 0

    overall_heat = min(100, int((opp_score * 0.6 + gap_score * 0.4)))
    heat_label = "حار جداً 🔥🔥" if overall_heat > 75 else \
                 "حار 🔥" if overall_heat > 50 else \
                 "متوسط 📊" if overall_heat > 25 else "هادئ 💤"

    insights = []
    if opportunities:
        o = opportunities[0]
        insights.append(f"أبرز فرصة: **{o['label']}** — تكررت {o['frequency']} مرة في {len(o.get('active_chats', []))} محادثة")
    if gaps:
        g = gaps[0]
        insights.append(f"أبرز ثغرة: **{g['label']}** — {g.get('opportunity', '')}")
    if topics:
        top3 = " • ".join(t["term"] for t in topics[:3])
        insights.append(f"أبرز المواضيع: {top3}")

    return {
        "total_messages": total,
        "opportunity_count": len(opportunities),
        "gap_count": len(gaps),
        "top_opportunity": top_opp,
        "top_gap": top_gap,
        "dominant_topic": top_topic,
        "market_heat": heat_label,
        "overall_score": overall_heat,
        "insights": insights,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ─── Main Entry ───────────────────────────────────────────────────────────────

def run_deep_analysis(messages: List[Dict]) -> Dict[str, Any]:
    """
    Full deep market intelligence pipeline.
    Input: list of message dicts from DB.
    Output: structured market report dict.
    """
    if not messages:
        return {
            "error": "لا توجد رسائل للتحليل",
            "generated_at": datetime.utcnow().isoformat(),
        }

    # Filter incoming messages only for analysis (not our own outgoing messages)
    incoming = [m for m in messages if m.get("direction") != "outgoing"]
    corpus = incoming if incoming else messages

    topics = extract_topics(corpus)
    opportunities = detect_opportunities(corpus)
    gaps = detect_gaps(corpus)
    demand = detect_demand_signals(corpus)
    trends = trend_analysis(corpus)
    channels = channel_insights(corpus)
    summary = executive_summary(opportunities, gaps, topics, corpus)

    return {
        "summary": summary,
        "topics": topics,
        "opportunities": opportunities,
        "gaps": gaps,
        "demand_signals": demand,
        "trends": trends,
        "channel_insights": channels,
        "generated_at": datetime.utcnow().isoformat(),
    }
