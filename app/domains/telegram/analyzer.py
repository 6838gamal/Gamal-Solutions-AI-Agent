"""
Deep Market Intelligence Engine for Telegram messages.
Pure Python — no external AI/ML dependencies required.
Follows the Knowledge Architecture framework:
  Priority = Pain × Frequency × Affected Count × Payment Probability
  Ranking: A (immediate) → B (strong) → C (future) → D (low value)
"""
import re
import math
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any

# ─── Stop Words ───────────────────────────────────────────────────────────────

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

# ─── Keyword Category Banks ────────────────────────────────────────────────────

KEYWORD_CATEGORIES: Dict[str, Dict] = {
    "مشاكل": {
        "label": "⚠️ مشاكل",
        "color": "red",
        "keywords": ["مشكلة","خطأ","معطل","لا يعمل","بطيء","سيء","رديء","فشل","ضعيف",
                     "شكوى","error","problem","broken","fail","slow","issue","bug"],
    },
    "طلبات": {
        "label": "🙋 طلبات",
        "color": "blue",
        "keywords": ["أريد","أبغى","أحتاج","محتاج","ممكن","ابغى","طلب","أطلب",
                     "need","want","request","require","looking for","searching"],
    },
    "حلول": {
        "label": "✅ حلول",
        "color": "green",
        "keywords": ["حل","يمكن","ممكن نحل","جرب","استخدم","نصيحة","توصية",
                     "solution","fix","resolve","try","recommend","guide","tip"],
    },
    "شراء": {
        "label": "🛒 شراء",
        "color": "emerald",
        "keywords": ["اشتري","سعر","ثمن","بكم","شراء","دفع","طلبية","order",
                     "buy","purchase","price","cost","pay","checkout","invoice"],
    },
    "أتمتة": {
        "label": "🤖 أتمتة",
        "color": "purple",
        "keywords": ["تلقائي","أتمتة","بوت","روبوت","جدولة","automate","bot",
                     "automation","schedule","trigger","workflow","automatic"],
    },
    "إدارة": {
        "label": "⚙️ إدارة",
        "color": "slate",
        "keywords": ["إدارة","تنظيم","متابعة","تقرير","لوحة","dashboard","manage",
                     "admin","organize","monitor","track","report","control"],
    },
    "نمو": {
        "label": "📈 نمو",
        "color": "amber",
        "keywords": ["نمو","توسع","تسويق","عملاء جدد","انتشار","grow","growth",
                     "marketing","scale","expand","audience","reach","viral"],
    },
    "دعم_فني": {
        "label": "🛠️ دعم فني",
        "color": "orange",
        "keywords": ["دعم","مساعدة","تواصل","رقم","واتساب","support","help",
                     "contact","technical","assistance","service","helpdesk"],
    },
}

# ─── Market Signal Keyword Banks ──────────────────────────────────────────────

OPPORTUNITY_PATTERNS: Dict[str, Dict] = {
    "طلب_منتج": {
        "label": "🎯 طلبات منتج/خدمة مباشرة",
        "keywords": ["أريد","أبغى","أبحث","محتاج","محتاجة","ابغى","أحتاج","ممكن توفر",
                     "need","want","looking for","searching","where can i"],
        "action": "الرد الفوري على طلبات العملاء وتحويلها إلى صفقات",
        "current_solutions": "ردود يدوية متأخرة",
        "solution_weaknesses": "بطيء وغير منتظم",
        "ai_opportunity": "ردود فورية بالذكاء الاصطناعي حسب نوع الطلب",
        "weight": 10, "pain": 3, "payment_prob": 4,
    },
    "استفسار_سعر": {
        "label": "💰 استفسارات الأسعار",
        "keywords": ["كم سعر","كم ثمن","كم تكلفة","سعر","ثمن","بكم","تكلفة",
                     "price","cost","how much","pricing","fee","rate","quote"],
        "action": "توضيح هيكل الأسعار وتقديم عروض قيمة مباشرة",
        "current_solutions": "قوائم أسعار ثابتة",
        "solution_weaknesses": "لا تأخذ احتياج العميل بعين الاعتبار",
        "ai_opportunity": "تسعير ديناميكي وعروض مخصصة بالذكاء الاصطناعي",
        "weight": 12, "pain": 4, "payment_prob": 5,
    },
    "مقارنة_منافس": {
        "label": "🆚 مقارنات بالمنافسين",
        "keywords": ["مقارنة","أفضل من","أحسن","بديل","بدلاً من","غيره","بدل",
                     "versus","vs","compare","better than","alternative","instead"],
        "action": "تطوير نقاط التميز والرد الاستراتيجي على المقارنات",
        "current_solutions": "ردود يدوية دفاعية",
        "solution_weaknesses": "غير منهجية وتفتقر للبيانات",
        "ai_opportunity": "تحليل منافسين تلقائي وردود مبنية على البيانات",
        "weight": 14, "pain": 4, "payment_prob": 4,
    },
    "فرصة_شراكة": {
        "label": "🤝 فرص شراكة وتوزيع",
        "keywords": ["تعاون","شراكة","توزيع","وكالة","عمولة","وكيل","تجار",
                     "partner","partnership","collaborate","distribute","commission","wholesale","reseller"],
        "action": "التواصل المباشر مع المهتمين وبناء شبكة توزيع",
        "current_solutions": "لا توجد قنوات شراكة رسمية",
        "solution_weaknesses": "ضياع الفرص في الفوضى",
        "ai_opportunity": "فرز وتأهيل الشركاء المحتملين تلقائياً",
        "weight": 18, "pain": 3, "payment_prob": 5,
    },
    "طلب_ميزة": {
        "label": "✨ طلبات تطوير وميزات",
        "keywords": ["ممكن تضيف","هل يدعم","لو كان فيه","أتمنى","نتمنى","لو يوجد",
                     "can you add","does it support","wish","feature request","would be nice"],
        "action": "إدراج الطلبات في خارطة التطوير وإبلاغ العملاء بالتحديثات",
        "current_solutions": "جمع ملاحظات يدوي",
        "solution_weaknesses": "بدون أولوية أو قياس",
        "ai_opportunity": "تصنيف وأولوية طلبات الميزات تلقائياً بالذكاء الاصطناعي",
        "weight": 8, "pain": 2, "payment_prob": 3,
    },
    "مخاوف_جودة": {
        "label": "🔍 مخاوف الجودة والأصالة",
        "keywords": ["جودة","ضمان","أصلي","مغشوش","اصل","تقليد","مزور",
                     "quality","guarantee","original","authentic","warranty","fake","counterfeit"],
        "action": "تعزيز ضمانات الجودة والشهادات لبناء الثقة",
        "current_solutions": "ضمانات نصية فقط",
        "solution_weaknesses": "لا يوجد تحقق قابل للإثبات",
        "ai_opportunity": "نظام تحقق رقمي وتوثيق أصالة بالذكاء الاصطناعي",
        "weight": 11, "pain": 4, "payment_prob": 3,
    },
    "خدمة_عملاء": {
        "label": "📞 طلبات خدمة العملاء",
        "keywords": ["مساعدة","دعم","تواصل","تواصلوا","كلموني","رقم","واتساب",
                     "help","support","contact","reach out","phone","customer service"],
        "action": "تحسين قنوات الدعم وسرعة الاستجابة",
        "current_solutions": "واتساب وتليجرام يدوي",
        "solution_weaknesses": "تأخير في الرد وعدم الاتساق",
        "ai_opportunity": "وكيل ذكاء اصطناعي يرد فورياً 24/7",
        "weight": 9, "pain": 4, "payment_prob": 4,
    },
}

GAP_DEFINITIONS: Dict[str, Dict] = {
    "أسئلة_متكررة": {
        "label": "❓ أسئلة متكررة بلا إجابات",
        "keywords": ["؟","?","كيف","ماذا","هل","لماذا","متى","أين","من أين","ما هو"],
        "opportunity": "تحويل هذه الأسئلة لمحتوى تسويقي وصفحات FAQ تجذب العملاء",
        "weight": 8, "pain": 3, "payment_prob": 2,
    },
    "شكاوى_متكررة": {
        "label": "⚠️ نقاط ألم متكررة",
        "keywords": ["مشكلة","خطأ","لا يعمل","معطل","سيء","رديء","ضعيف","بطيء",
                     "problem","issue","error","not working","broken","slow","bad"],
        "opportunity": "معالجة هذه المشاكل يفتح فرص تميّز واضح على المنافسين",
        "weight": 14, "pain": 5, "payment_prob": 4,
    },
    "حساسية_السعر": {
        "label": "💸 حساسية السعر — فرصة تسعير",
        "keywords": ["غالي","باهظ","مو مناسب","مش مناسب","كثير","ما يستاهل",
                     "expensive","overpriced","too much","not worth","costly"],
        "opportunity": "تقديم حزم مرنة وعروض قيمة تناسب شرائح مختلفة",
        "weight": 13, "pain": 4, "payment_prob": 5,
    },
    "نقص_معلومات": {
        "label": "📚 نقص في المعلومات والمحتوى",
        "keywords": ["لا أعرف","ما أعرف","لا أجد","ما وجدت","ما لقيت","ما أدري",
                     "don't know","can't find","not sure","unclear","confused"],
        "opportunity": "إنتاج محتوى تعليمي وتسويقي يُعالج هذا الغموض",
        "weight": 7, "pain": 2, "payment_prob": 2,
    },
    "تأخر_التسليم": {
        "label": "🚚 مشاكل التسليم والانتظار",
        "keywords": ["متى","انتظر","تأخر","وصل","يصل","شحن","توصيل",
                     "when","waiting","delayed","shipping","delivery","tracking"],
        "opportunity": "تحسين الشفافية في عمليات التسليم وتقديم تتبع لحظي",
        "weight": 10, "pain": 4, "payment_prob": 3,
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


# ─── Priority Matrix (Knowledge Architecture) ─────────────────────────────────

def _priority_class(score: int) -> Dict:
    if score >= 70:
        return {"class": "A", "label": "يجب العمل عليه فوراً", "color": "red", "badge": "🔴 A"}
    elif score >= 45:
        return {"class": "B", "label": "فرصة قوية", "color": "amber", "badge": "🟡 B"}
    elif score >= 20:
        return {"class": "C", "label": "فرصة مستقبلية", "color": "blue", "badge": "🔵 C"}
    else:
        return {"class": "D", "label": "منخفضة القيمة", "color": "slate", "badge": "⚪ D"}


def priority_matrix(opportunities: List[Dict], gaps: List[Dict], messages: List[Dict]) -> List[Dict]:
    """
    Score each finding: Priority = Pain × Frequency × Affected × PaymentProb
    then classify as A/B/C/D.
    """
    total_chats = max(len({m.get("chat_id") for m in messages}), 1)
    results = []

    for opp in opportunities:
        key = opp.get("key", "")
        meta = OPPORTUNITY_PATTERNS.get(key, {})
        pain = meta.get("pain", 3)
        freq = min(5, max(1, opp.get("frequency", 1)))
        affected = min(5, max(1, len(opp.get("active_chats", []))))
        pay_prob = meta.get("payment_prob", 3)
        raw = pain * freq * affected * pay_prob
        score = min(100, int(raw * 1.5))
        priority = _priority_class(score)
        results.append({
            "label": opp["label"],
            "type": "فرصة",
            "frequency": opp.get("frequency", 0),
            "affected_chats": len(opp.get("active_chats", [])),
            "action": opp.get("action", ""),
            "ai_opportunity": meta.get("ai_opportunity", ""),
            "current_solutions": meta.get("current_solutions", ""),
            "solution_weaknesses": meta.get("solution_weaknesses", ""),
            "score": score,
            **priority,
        })

    for gap in gaps:
        key = gap.get("key", "")
        meta = GAP_DEFINITIONS.get(key, {})
        pain = meta.get("pain", 3)
        freq = min(5, max(1, gap.get("frequency", 1)))
        affected = min(5, int(total_chats * 0.4) + 1)
        pay_prob = meta.get("payment_prob", 2)
        raw = pain * freq * affected * pay_prob
        score = min(100, int(raw * 0.8))
        priority = _priority_class(score)
        results.append({
            "label": gap["label"],
            "type": "ثغرة",
            "frequency": gap.get("frequency", 0),
            "affected_chats": affected,
            "action": gap.get("opportunity", ""),
            "ai_opportunity": "تحليل الأنماط تلقائياً وتنبيه الفريق",
            "current_solutions": "غير محددة",
            "solution_weaknesses": "لا توجد معالجة منهجية",
            "score": score,
            **priority,
        })

    return sorted(results, key=lambda x: -x["score"])


# ─── Keyword Categories ────────────────────────────────────────────────────────

def keyword_categories(messages: List[Dict]) -> List[Dict]:
    """
    Extract and count keywords from messages, grouped by the 8 categories.
    """
    results = []
    for cat_key, cat in KEYWORD_CATEGORIES.items():
        matching_words: Counter = Counter()
        msg_count = 0
        for m in messages:
            content = (m.get("content", "") or "").lower()
            hits = [kw for kw in cat["keywords"] if kw.lower() in content]
            if hits:
                msg_count += 1
                for h in hits:
                    matching_words[h] += 1
        if msg_count == 0:
            continue
        results.append({
            "key": cat_key,
            "label": cat["label"],
            "color": cat["color"],
            "msg_count": msg_count,
            "top_keywords": [{"word": w, "count": c} for w, c in matching_words.most_common(6)],
            "intensity": "عالية 🔥" if msg_count > 20 else "متوسطة" if msg_count > 5 else "منخفضة",
        })
    return sorted(results, key=lambda x: -x["msg_count"])


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

        co: Counter = Counter()
        for m in related:
            for t in tokenize(m.get("content", "")):
                if t != term and t not in used:
                    co[t] += 1
        co_terms = [t for t, _ in co.most_common(4)]

        sentiments: Counter = Counter()
        for m in related:
            ar = m.get("analysis_result") or {}
            sentiments[ar.get("sentiment", "محايد")] += 1
        dominant = sentiments.most_common(1)[0][0] if sentiments else "محايد"

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
            "ai_opportunity": meta.get("ai_opportunity", ""),
            "current_solutions": meta.get("current_solutions", ""),
            "solution_weaknesses": meta.get("solution_weaknesses", ""),
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


# ─── User Intelligence (Buyer Radar) ──────────────────────────────────────────

BUYING_KW = ["اشتري","أشتري","أريد أشتري","ابغى اشتري","سعر","بكم","كم تكلفة","كم الثمن",
             "buy","purchase","price","how much","cost","order","checkout","pay"]
PAIN_KW   = ["مشكلة","خطأ","لا يعمل","معطل","تعبت","ضعيف","سيء","رديء",
             "problem","issue","broken","error","not working","frustrated","slow"]
INFLU_KW  = ["أنصح","أفضل","أقترح","recommend","suggest","best","من تجربتي","جربت"]

def user_intelligence(messages: List[Dict]) -> List[Dict]:
    """Build a buyer profile for every incoming sender."""
    by_user: Dict[str, List] = defaultdict(list)
    for m in messages:
        if m.get("direction") == "incoming":
            key = m.get("sender_name") or "مجهول"
            by_user[key].append(m)

    results = []
    for sender, msgs in by_user.items():
        total = len(msgs)
        content_all = " ".join((m.get("content","") or "") for m in msgs).lower()

        buying_msgs   = sum(1 for m in msgs if any(k in (m.get("content","") or "").lower() for k in BUYING_KW))
        pain_msgs     = sum(1 for m in msgs if any(k in (m.get("content","") or "").lower() for k in PAIN_KW))
        question_msgs = sum(1 for m in msgs if "؟" in (m.get("content","") or "") or "?" in (m.get("content","") or ""))
        influ_msgs    = sum(1 for m in msgs if any(k in (m.get("content","") or "").lower() for k in INFLU_KW))

        buying_prob   = min(100, int((buying_msgs / max(total,1)) * 200 + total * 1.5))
        influence_score = min(100, int((influ_msgs + question_msgs) / max(total,1) * 80 + total * 2))

        toks: Counter = Counter()
        for m in msgs:
            toks.update(tokenize(m.get("content","")))
        interests = [t for t, _ in toks.most_common(5)]
        chats     = list({m.get("chat_title","") for m in msgs if m.get("chat_title")})[:3]

        if buying_prob >= 60:
            readiness       = "جاهز للشراء 🔥"
            readiness_color = "red"
        elif buying_prob >= 35:
            readiness       = "مهتم ومتابع 👀"
            readiness_color = "amber"
        elif pain_msgs > 0:
            readiness       = "يعاني من مشكلة 😟"
            readiness_color = "orange"
        else:
            readiness       = "مراقب 👁️"
            readiness_color = "slate"

        username   = msgs[0].get("sender_username","") if msgs else ""
        last_msg   = max((m.get("received_at") or "" for m in msgs), default="")

        results.append({
            "sender":           sender,
            "username":         username,
            "message_count":    total,
            "buying_signals":   buying_msgs,
            "pain_signals":     pain_msgs,
            "question_count":   question_msgs,
            "buying_probability": buying_prob,
            "influence_score":  influence_score,
            "interests":        interests,
            "active_chats":     chats,
            "readiness":        readiness,
            "readiness_color":  readiness_color,
            "last_active":      str(last_msg)[:10] if last_msg else "—",
        })

    return sorted(results, key=lambda x: -x["buying_probability"])[:20]


# ─── Opportunity Clusters ──────────────────────────────────────────────────────

CLUSTER_DEFS = [
    {
        "name": "إدارة الأعمال والأتمتة",
        "icon": "⚙️",
        "color": "purple",
        "opp_keys": ["طلب_ميزة","طلب_منتج"],
        "desc": "الطلب على أدوات تنظيم وأتمتة العمليات التجارية",
        "market_size": "كبير جداً",
    },
    {
        "name": "خدمة العملاء الذكية",
        "icon": "📞",
        "color": "blue",
        "opp_keys": ["خدمة_عملاء","طلب_منتج"],
        "desc": "حاجة السوق لنظام دعم عملاء سريع وذكي 24/7",
        "market_size": "كبير",
    },
    {
        "name": "فرص البيع والتسعير",
        "icon": "💰",
        "color": "emerald",
        "opp_keys": ["استفسار_سعر","مخاوف_جودة"],
        "desc": "إشارات نية شراء قوية مع حساسية سعرية — فرصة تسعير مرن",
        "market_size": "متوسط",
    },
    {
        "name": "نمو الشبكة والشراكات",
        "icon": "🤝",
        "color": "amber",
        "opp_keys": ["فرصة_شراكة","مقارنة_منافس"],
        "desc": "فرص توسع عبر الشراكات التجارية وشبكات التوزيع",
        "market_size": "متوسط",
    },
]


def opportunity_clusters(messages: List[Dict], opportunities: List[Dict]) -> List[Dict]:
    """Group detected opportunities into compound market clusters."""
    opp_by_key = {o["key"]: o for o in opportunities}
    results = []

    for cdef in CLUSTER_DEFS:
        matched = [opp_by_key[k] for k in cdef["opp_keys"] if k in opp_by_key]
        if not matched:
            continue
        total_freq = sum(o.get("frequency", 0) for o in matched)
        if total_freq < 1:
            continue
        avg_score  = int(sum(o.get("score", 0) for o in matched) / max(len(matched), 1))
        all_chats  = list({c for o in matched for c in (o.get("active_chats") or [])})[:5]
        comp_score = min(100, total_freq * 4 + avg_score // 2)

        results.append({
            "name":         cdef["name"],
            "icon":         cdef["icon"],
            "color":        cdef["color"],
            "description":  cdef["desc"],
            "market_size":  cdef["market_size"],
            "total_messages": total_freq,
            "avg_score":    avg_score,
            "composite_score": comp_score,
            "active_chats": all_chats,
            "sub_opportunities": [
                {"label": o["label"], "freq": o["frequency"], "score": o["score"]}
                for o in matched
            ],
        })

    return sorted(results, key=lambda x: -x["composite_score"])


# ─── Silent Market Gaps ────────────────────────────────────────────────────────

SILENT_PATTERNS = [
    {
        "key": "crm_demand",
        "label": "🏢 CRM — إدارة علاقات العملاء",
        "keywords": ["إدارة عملاء","قاعدة عملاء","متابعة عملاء","crm","customer management","عميل","client"],
        "gap": "السوق يبحث عن CRM مبسط — فجوة واضحة في الحلول المتاحة",
    },
    {
        "key": "automation_gap",
        "label": "🤖 أتمتة المهام اليدوية",
        "keywords": ["يدوي","تعبت","مرهق","وقت طويل","بطيء","manual","tedious","time consuming","عمل يدوي"],
        "gap": "شكاوى من العمل اليدوي دون وجود حل أتمتة كافٍ",
    },
    {
        "key": "analytics_gap",
        "label": "📊 تقارير وتحليلات الأعمال",
        "keywords": ["تقرير","إحصاء","أداء","نتائج","إحصائيات","report","analytics","statistics","performance"],
        "gap": "طلب متكرر على التقارير التحليلية دون توفرها بشكل كافٍ",
    },
    {
        "key": "training_gap",
        "label": "📚 محتوى تعليمي وتدريبي",
        "keywords": ["كيف","تعلم","شرح","دورة","تدريب","course","tutorial","learn","how to","شرح لي"],
        "gap": "احتياج واضح للمحتوى التعليمي — السوق يسأل ولا يجد إجابات كافية",
    },
    {
        "key": "integration_gap",
        "label": "🔗 ربط الأنظمة والتكامل",
        "keywords": ["ربط","تكامل","api","متصل","واجهة برمجية","integrate","connect","sync","webhook"],
        "gap": "طلب على ربط الأنظمة المتعددة — سوق التكاملات غير مشبَع",
    },
    {
        "key": "pricing_gap",
        "label": "💸 حلول تسعير مرنة",
        "keywords": ["غالي","باهظ","مو مناسب","مش مناسب","ما يستاهل","expensive","overpriced","too much","costly","حزمة أرخص"],
        "gap": "حساسية سعرية عالية — فرصة تقديم حزم مرنة وأسعار تنافسية",
    },
]

SOLUTION_WORDS = ["استخدم","جرب","ننصح","موجود","يوجد","توجد","حل","available",
                  "solution","try","use","found","وجدنا","لقينا"]


def silent_market_gaps(messages: List[Dict]) -> List[Dict]:
    """Detect market needs that are frequently mentioned but rarely answered."""
    results = []
    for pat in SILENT_PATTERNS:
        matching = [m for m in messages
                    if any(k.lower() in (m.get("content","") or "").lower() for k in pat["keywords"])]
        if not matching:
            continue
        freq = len(matching)
        sol_count = sum(1 for m in matching
                        if any(sw in (m.get("content","") or "").lower() for sw in SOLUTION_WORDS))
        intensity = freq - sol_count
        if intensity < 1:
            continue
        score = min(100, intensity * 12)
        chats  = list({m.get("chat_title","") for m in matching if m.get("chat_title")})[:3]
        sample = next((m.get("content","")[:120] for m in matching if m.get("content","")), "")

        results.append({
            "key":             pat["key"],
            "label":           pat["label"],
            "gap":             pat["gap"],
            "total_mentions":  freq,
            "solution_mentions": sol_count,
            "gap_intensity":   intensity,
            "score":           score,
            "active_chats":    chats,
            "sample":          sample,
            "severity": "حرج 🔴" if intensity > 10 else "عالٍ 🟡" if intensity > 4 else "متوسط 🔵",
        })

    return sorted(results, key=lambda x: -x["score"])


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


def executive_dashboard(opportunities: List, gaps: List, topics: List,
                        demand: List, kw_cats: List, messages: List) -> Dict:
    """
    8-row executive dashboard table as per the Knowledge Architecture framework.
    """
    total = len(messages)

    # Biggest problem
    top_gap = gaps[0]["label"] if gaps else "—"

    # Most affected category
    chats_by_type: Counter = Counter()
    for m in messages:
        chats_by_type[m.get("chat_type", "غير محدد")] += 1
    most_affected = chats_by_type.most_common(1)[0][0] if chats_by_type else "—"
    type_map = {"user": "المستخدمون الأفراد", "group": "المجموعات", "channel": "القنوات"}
    most_affected = type_map.get(most_affected, most_affected)

    # Highest revenue opportunity
    top_opp = opportunities[0]["label"] if opportunities else "—"
    top_opp_ai = opportunities[0].get("ai_opportunity", "—") if opportunities else "—"

    # Fastest to implement
    fastest = "—"
    for opp in opportunities:
        if opp.get("frequency", 0) > 2:
            fastest = opp["label"]
            break

    # Least competition (lowest score with highest pain)
    least_comp = "—"
    for opp in reversed(opportunities):
        if opp.get("score", 0) < 40:
            least_comp = opp["label"]
            break

    # Highest demand
    top_demand = demand[0]["label"] if demand else (top_opp if opportunities else "—")

    # Most sellable
    top_sellable = "—"
    for opp in opportunities:
        key = opp.get("key", "")
        meta = OPPORTUNITY_PATTERNS.get(key, {})
        if meta.get("payment_prob", 0) >= 4:
            top_sellable = opp["label"]
            break

    # Top AI opportunity
    top_ai = "—"
    for item in opportunities:
        if item.get("ai_opportunity"):
            top_ai = item["ai_opportunity"]
            break

    # Overall heat
    opp_score = opportunities[0]["score"] if opportunities else 0
    gap_score = gaps[0]["score"] if gaps else 0
    overall_heat = min(100, int((opp_score * 0.6 + gap_score * 0.4)))
    heat_label = "حار جداً 🔥🔥" if overall_heat > 75 else \
                 "حار 🔥" if overall_heat > 50 else \
                 "متوسط 📊" if overall_heat > 25 else "هادئ 💤"

    # Key insights
    insights = []
    if opportunities:
        o = opportunities[0]
        insights.append(f"أبرز فرصة: **{o['label']}** — تكررت {o['frequency']} مرة")
    if gaps:
        g = gaps[0]
        insights.append(f"أبرز ثغرة: **{g['label']}** — {g.get('opportunity', '')}")
    if topics:
        top3 = " • ".join(t["term"] for t in topics[:3])
        insights.append(f"أبرز المواضيع: {top3}")

    return {
        "rows": [
            {"label": "أكبر مشكلة", "icon": "⚠️", "value": top_gap, "color": "red"},
            {"label": "أكثر فئة متضررة", "icon": "👥", "value": most_affected, "color": "orange"},
            {"label": "أعلى فرصة ربح", "icon": "💎", "value": top_opp, "color": "emerald"},
            {"label": "أسرع فرصة تنفيذ", "icon": "⚡", "value": fastest, "color": "blue"},
            {"label": "أقل منافسة", "icon": "🏆", "value": least_comp, "color": "purple"},
            {"label": "أعلى طلب", "icon": "📈", "value": top_demand, "color": "amber"},
            {"label": "أعلى قابلية للبيع", "icon": "🛒", "value": top_sellable, "color": "green"},
            {"label": "أعلى فرصة AI", "icon": "🤖", "value": top_ai, "color": "indigo"},
        ],
        "total_messages": total,
        "opportunity_count": len(opportunities),
        "gap_count": len(gaps),
        "market_heat": heat_label,
        "overall_score": overall_heat,
        "insights": insights,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ─── Main Entry ───────────────────────────────────────────────────────────────

def run_deep_analysis(messages: List[Dict]) -> Dict[str, Any]:
    if not messages:
        return {
            "error": "لا توجد رسائل للتحليل",
            "generated_at": datetime.utcnow().isoformat(),
        }

    incoming = [m for m in messages if m.get("direction") != "outgoing"]
    corpus = incoming if incoming else messages

    topics        = extract_topics(corpus)
    opportunities = detect_opportunities(corpus)
    gaps          = detect_gaps(corpus)
    demand        = detect_demand_signals(corpus)
    trends        = trend_analysis(corpus)
    channels      = channel_insights(corpus)
    kw_cats       = keyword_categories(corpus)
    matrix        = priority_matrix(opportunities, gaps, corpus)
    dashboard     = executive_dashboard(opportunities, gaps, topics, demand, kw_cats, corpus)
    buyer_radar   = user_intelligence(corpus)
    clusters      = opportunity_clusters(corpus, opportunities)
    silent_gaps   = silent_market_gaps(corpus)

    return {
        "summary":             dashboard,
        "priority_matrix":     matrix,
        "keyword_categories":  kw_cats,
        "topics":              topics,
        "opportunities":       opportunities,
        "gaps":                gaps,
        "demand_signals":      demand,
        "trends":              trends,
        "channel_insights":    channels,
        "buyer_radar":         buyer_radar,
        "opportunity_clusters": clusters,
        "silent_market_gaps":  silent_gaps,
        "generated_at":        datetime.utcnow().isoformat(),
    }
