"""
RAG Pipeline v3.0 — Production-grade Knowledge Processing System
================================================================
Pipeline:
  Clean → Lang Detect → Section Detect → Semantic Chunk (with overlap)
  → Keyword Extraction (BM25-ready) → Question Generation → Entity Extraction
  → Fact Extraction → Intent Classification → JSON Build

Retrieval:
  Query Expansion (synonyms) → BM25 Scoring → Multi-signal Reranking
  → Confidence Scoring → Top-K Results
"""
import re
import json
import math
import logging
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "3.0"

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & VOCABULARIES
# ══════════════════════════════════════════════════════════════════════════════

ARABIC_STOP = {
    "من", "في", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "تلك",
    "التي", "الذي", "الذين", "ما", "أن", "كان", "كانت", "يكون", "تكون",
    "قد", "لم", "لن", "لا", "إن", "إذا", "عند", "بعد", "قبل", "أو", "و",
    "ثم", "حتى", "كما", "أيضاً", "أيضا", "هو", "هي", "هم", "هن", "أنت",
    "أنا", "نحن", "أنتم", "يتم", "تم", "كل", "بعض", "غير", "حول", "خلال",
    "ضمن", "أكثر", "أقل", "جداً", "جدا", "وفق", "وفقاً", "حيث", "به",
    "بها", "لها", "له", "بهم", "لهم", "منه", "منها", "هناك", "هنا",
    "أمام", "خلف", "فوق", "تحت", "عبر", "خلاله", "خلالها", "ولا", "وما",
    "إلا", "فإن", "وإن", "ومن", "وفي", "وعلى", "وإلى", "عليه", "عليها",
    "فيه", "فيها", "منها", "عنه", "عنها", "لذلك", "وذلك", "بذلك",
}

ENGLISH_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "on", "at", "by", "for", "with", "about", "from", "as", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "and", "or", "but", "if", "then", "that", "this", "these", "those",
    "it", "its", "they", "their", "them", "we", "our", "you", "your",
    "he", "she", "his", "her", "i", "my", "not", "no", "nor", "so", "up",
    "also", "just", "which", "when", "where", "who", "what", "how", "all",
}

STOP_WORDS = ARABIC_STOP | ENGLISH_STOP

ORG_PREFIXES = [
    "شركة", "مؤسسة", "هيئة", "وزارة", "مجلس", "لجنة", "مركز",
    "إدارة", "دائرة", "جمعية", "بنك", "صندوق", "جهاز", "منظمة",
]

# ── Synonym dictionary for query expansion ────────────────────────────────────
ARABIC_SYNONYMS: dict[str, list[str]] = {
    "سعر":       ["تكلفة", "رسوم", "قيمة", "ثمن", "مبلغ", "أجر"],
    "تكلفة":     ["سعر", "رسوم", "قيمة", "ثمن", "مبلغ"],
    "رسوم":      ["سعر", "تكلفة", "قيمة", "ثمن", "مبلغ"],
    "قيمة":      ["سعر", "تكلفة", "رسوم"],
    "اشتراك":    ["عضوية", "تسجيل", "انضمام", "خطة"],
    "عضوية":     ["اشتراك", "تسجيل", "انضمام"],
    "خدمة":      ["منتج", "حل", "برنامج", "نظام"],
    "منتج":      ["خدمة", "حل", "برنامج"],
    "مشكلة":     ["عطل", "خلل", "خطأ", "عيب", "أزمة"],
    "عطل":       ["مشكلة", "خلل", "خطأ"],
    "خطأ":       ["مشكلة", "عطل", "خلل"],
    "حل":        ["معالجة", "إصلاح", "تصحيح", "تسوية"],
    "إصلاح":     ["حل", "معالجة", "تصحيح"],
    "طلب":       ["استفسار", "سؤال", "احتياج", "تقديم"],
    "استفسار":   ["طلب", "سؤال", "تساؤل"],
    "دفع":       ["سداد", "تسديد", "إيداع", "تحويل"],
    "سداد":      ["دفع", "تسديد", "إيداع"],
    "تواصل":     ["اتصال", "مراسلة", "تحدث"],
    "اتصال":     ["تواصل", "مراسلة"],
    "شركة":      ["مؤسسة", "منظمة", "جهة", "هيئة"],
    "مؤسسة":     ["شركة", "منظمة", "جهة"],
    "عميل":      ["مشترك", "زبون", "مستخدم", "مستفيد"],
    "مستخدم":    ["عميل", "مشترك", "زبون"],
    "زبون":      ["عميل", "مشترك", "مستخدم"],
    "حساب":      ["اشتراك", "ملف", "بيانات"],
    "بيانات":    ["معلومات", "تفاصيل", "سجلات"],
    "معلومات":   ["بيانات", "تفاصيل"],
    "ضمان":      ["كفالة", "تأمين", "ضمانة"],
    "تسليم":     ["توصيل", "شحن", "إيصال", "استلام"],
    "توصيل":     ["تسليم", "شحن", "إيصال"],
    "إلغاء":     ["فسخ", "إنهاء", "إيقاف"],
    "إنهاء":     ["إلغاء", "فسخ", "إيقاف"],
    "تجديد":     ["تمديد", "تحديث", "استمرار"],
    "موعد":      ["وقت", "توقيت", "ميعاد", "أجل"],
    "خطوات":     ["مراحل", "إجراءات", "طريقة", "آلية"],
    "إجراءات":   ["خطوات", "مراحل", "طريقة"],
    "شروط":      ["متطلبات", "اشتراطات", "ضوابط", "معايير"],
    "متطلبات":   ["شروط", "اشتراطات", "ضوابط"],
    "سياسة":     ["لائحة", "نظام", "قانون", "تعليمات"],
    "لائحة":     ["سياسة", "نظام", "قرار"],
    "وثيقة":     ["مستند", "ملف", "عقد"],
    "مستند":     ["وثيقة", "ملف", "سجل"],
    "تقرير":     ["بيان", "ملخص", "كشف"],
    "فاتورة":    ["كشف حساب", "إيصال", "وصل"],
    "استرداد":   ["استرجاع", "إعادة", "رد"],
}

ENGLISH_SYNONYMS: dict[str, list[str]] = {
    "price":        ["cost", "fee", "charge", "rate", "amount"],
    "cost":         ["price", "fee", "charge", "rate"],
    "fee":          ["price", "cost", "charge", "rate"],
    "subscription": ["membership", "plan", "account", "enrollment"],
    "membership":   ["subscription", "plan", "account"],
    "service":      ["product", "solution", "offering", "feature"],
    "product":      ["service", "solution", "offering"],
    "issue":        ["problem", "error", "bug", "fault", "trouble"],
    "problem":      ["issue", "error", "bug", "fault"],
    "error":        ["issue", "problem", "bug", "fault"],
    "solution":     ["fix", "resolution", "answer", "remedy"],
    "fix":          ["solution", "resolution", "repair"],
    "payment":      ["billing", "charge", "invoice", "transaction"],
    "billing":      ["payment", "charge", "invoice"],
    "cancel":       ["terminate", "stop", "end", "discontinue"],
    "terminate":    ["cancel", "stop", "end"],
    "renew":        ["extend", "refresh", "update", "continue"],
    "customer":     ["client", "user", "subscriber", "member"],
    "user":         ["customer", "client", "subscriber"],
    "client":       ["customer", "user", "subscriber"],
    "account":      ["profile", "subscription", "membership"],
    "contact":      ["reach", "call", "email", "connect"],
    "support":      ["help", "assistance", "service", "aid"],
    "help":         ["support", "assistance", "guidance"],
    "delivery":     ["shipping", "dispatch", "shipment"],
    "shipping":     ["delivery", "dispatch"],
    "refund":       ["return", "reimbursement", "rebate"],
    "warranty":     ["guarantee", "coverage", "assurance"],
    "policy":       ["rule", "regulation", "guideline", "procedure"],
    "procedure":    ["process", "steps", "method", "guideline"],
    "requirement":  ["condition", "prerequisite", "criteria"],
    "document":     ["file", "record", "contract", "agreement"],
    "invoice":      ["bill", "receipt", "statement"],
    "discount":     ["offer", "promotion", "deal", "reduction"],
}


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1: TEXT CLEANING
# ══════════════════════════════════════════════════════════════════════════════

def clean_text(text: str) -> str:
    """Remove noise while preserving structure and meaning."""
    if not text:
        return ""
    # Invisible/control characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0]", " ", text)
    text = re.sub(r"[\r\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize Arabic letter variants (but keep ى vs ي distinction for now)
    text = re.sub(r"[إأآ]", "ا", text)
    text = re.sub(r"ة\b", "ه", text)   # ta marbuta normalization
    # Normalize whitespace — keep newlines for structure
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Repeated punctuation
    text = re.sub(r"\.{3,}", "...", text)
    text = re.sub(r"-{3,}", "—", text)
    text = re.sub(r"={2,}", "", text)
    text = re.sub(r"\*{2,}", "", text)
    return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2: LANGUAGE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[\u0600-\u06ff]", text))
    english = len(re.findall(r"[a-zA-Z]", text))
    if arabic > english * 1.5:
        return "ar"
    if english > arabic * 1.5:
        return "en"
    return "mixed"


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3: SECTION DETECTION (improved — captures more heading patterns)
# ══════════════════════════════════════════════════════════════════════════════

def detect_sections(text: str) -> list:
    """
    Identifies document sections by heuristic heading detection.
    Returns list of {heading, text} dicts.
    """
    lines = text.split("\n")
    sections = []
    current: dict = {"heading": None, "text": []}

    heading_re = re.compile(
        r"^(?:"
        r"\d+[\.\-\)]\s+[^\d]"       # numbered: 1. Title
        r"|[أ-ي][\.\-\)]\s+"          # Arabic letter bullet
        r"|#{1,3}\s+"                  # Markdown headers
        r"|\*\*[^*]+\*\*"             # Bold markdown
        r")"
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_heading = bool(
            (len(line) < 120 and (
                line.endswith(":") or
                line.endswith("：") or
                (line.isupper() and 3 <= len(line.split()) <= 10) or
                line.startswith("#") or
                bool(heading_re.match(line))
            ))
        )

        if is_heading:
            if current["text"]:
                sections.append(current)
            heading_clean = re.sub(r"^#+\s*|\*\*|\s*:$|：$", "", line).strip()
            current = {"heading": heading_clean, "text": []}
        else:
            current["text"].append(line)

    if current["text"] or current["heading"]:
        sections.append(current)

    return [
        {"heading": s["heading"], "text": " ".join(s["text"])}
        for s in sections
        if s["text"]
    ]


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4: SEMANTIC CHUNKING WITH OVERLAP
# ══════════════════════════════════════════════════════════════════════════════

def semantic_chunk_with_overlap(
    text: str,
    sections: list,
    max_chars: int = 600,
    min_chars: int = 80,
    overlap_chars: int = 100,
) -> list:
    """
    Improved chunker:
    - Respects section boundaries (each section chunked independently)
    - Sliding window overlap between consecutive chunks (reduces boundary loss)
    - Returns chunks with section context
    """
    all_chunks = []
    chunk_id = 1

    def _split_into_chunks(block_text: str, heading: str | None) -> list:
        nonlocal chunk_id
        result = []
        paragraphs = [p.strip() for p in block_text.split("\n\n") if p.strip()]
        buffer: list[str] = []
        buf_len = 0

        def flush(buf: list[str]) -> None:
            nonlocal chunk_id
            joined = " ".join(buf)
            if len(joined) >= min_chars:
                result.append({
                    "id": chunk_id,
                    "text": joined,
                    "section_heading": heading,
                    "chars": len(joined),
                    "words": len(joined.split()),
                })
                chunk_id += 1

        for para in paragraphs:
            if len(para) > max_chars:
                if buffer:
                    flush(buffer)
                    buffer, buf_len = [], 0
                sentences = re.split(r"(?<=[.!?؟،])\s+", para)
                sb: list[str] = []
                sl = 0
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if sl + len(sent) > max_chars and sb:
                        flush(sb)
                        # Overlap: carry last sentence into next chunk
                        overlap_sents = sb[-1:] if sb else []
                        sb = overlap_sents + [sent]
                        sl = sum(len(s) for s in sb)
                    else:
                        sb.append(sent)
                        sl += len(sent)
                if sb:
                    flush(sb)
            elif buf_len + len(para) > max_chars:
                if buffer:
                    # Overlap: carry last paragraph into next chunk
                    overlap_text = buffer[-1] if buffer else ""
                    flush(buffer)
                    if overlap_text and len(overlap_text) <= overlap_chars:
                        buffer = [overlap_text, para]
                        buf_len = len(overlap_text) + len(para)
                    else:
                        buffer = [para]
                        buf_len = len(para)
                else:
                    buffer = [para]
                    buf_len = len(para)
            else:
                buffer.append(para)
                buf_len += len(para)

        if buffer:
            flush(buffer)

        return result

    if sections:
        for sec in sections:
            sec_text = sec.get("text", "")
            heading = sec.get("heading")
            if sec_text.strip():
                all_chunks.extend(_split_into_chunks(sec_text, heading))
    else:
        all_chunks.extend(_split_into_chunks(text, None))

    return all_chunks


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def tokenize(text: str) -> set[str]:
    """Extract meaningful tokens, remove stop words."""
    text = re.sub(r"[إأآ]", "ا", text.lower())
    words = re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", text)
    return {w for w in words if w not in STOP_WORDS}


def tokenize_with_freq(text: str) -> Counter:
    """Tokenize and count term frequencies."""
    text = re.sub(r"[إأآ]", "ا", text.lower())
    words = re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", text)
    return Counter(w for w in words if w not in STOP_WORDS)


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5a: KEYWORD EXTRACTION (chunk-level, TF-IDF style)
# ══════════════════════════════════════════════════════════════════════════════

def extract_keywords(text: str, top_n: int = 15) -> list:
    """
    Per-chunk keyword extraction using TF × log(1 + len(word)) as IDF proxy.
    Also extracts bigrams for multi-word terms.
    """
    # Unigrams
    words = re.findall(r"[\u0600-\u06ff]{3,}|[a-zA-Z]{4,}", re.sub(r"[إأآ]", "ا", text.lower()))
    words = [w for w in words if w not in STOP_WORDS]
    if not words:
        return []

    freq = Counter(words)
    total = len(words)
    scored = []
    for word, count in freq.most_common(top_n * 3):
        tf = count / total
        idf_proxy = math.log(1 + len(word))
        scored.append({"term": word, "count": count, "score": round(tf * idf_proxy, 5)})

    # Bigrams (adjacent meaningful word pairs)
    bigrams = []
    for i in range(len(words) - 1):
        bg = f"{words[i]} {words[i+1]}"
        bigrams.append(bg)
    bigram_freq = Counter(bigrams)
    for bg, count in bigram_freq.most_common(5):
        if count >= 2:  # only repeated bigrams
            scored.append({"term": bg, "count": count, "score": round((count / total) * 2.0, 5)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5b: QUESTION GENERATION (template-based, per chunk)
# ══════════════════════════════════════════════════════════════════════════════

def generate_questions(
    chunk_text: str,
    section_heading: str | None,
    lang: str,
    keywords: list,
) -> list[str]:
    """
    Generate 3–6 questions that this chunk likely answers.
    Uses rule-based templates tailored to Arabic and English content.
    """
    questions: list[str] = []
    kw = [k["term"] for k in keywords[:4]]
    text_lower = chunk_text.lower()

    # ── Arabic templates ──────────────────────────────────────────────────
    if lang in ("ar", "mixed"):

        # Q1: "ما هو/هي [keyword]؟"
        if kw:
            questions.append(f"ما هو {kw[0]}؟")
        if len(kw) > 1:
            questions.append(f"ما هي {kw[1]}؟")

        # Q2: Section-heading question
        if section_heading and len(section_heading) > 2:
            questions.append(f"ما هي {section_heading}؟")

        # Q3: Process/steps detection
        if re.search(r"(?:خطوه|خطوة|أولاً|ثانياً|أولا|ثانيا|\d+[\.\-\)])", chunk_text):
            topic = kw[0] if kw else (section_heading or "العملية")
            questions.append(f"ما هي خطوات {topic}؟")
            questions.append(f"كيف أقوم بـ {topic}؟")

        # Q4: Definition detection
        if re.search(r"(?:يُعرَّف|يعرف|تُعرف|هو|هي|تعني|يعني|المقصود|يقصد)", chunk_text[:300]):
            if kw:
                questions.append(f"ما تعريف {kw[0]}؟")
                questions.append(f"ماذا يعني {kw[0]}؟")

        # Q5: Requirement/condition detection
        if re.search(r"(?:يجب|ينبغي|يلزم|مطلوب|شرط|شروط|متطلبات|اشتراط)", chunk_text):
            topic = kw[0] if kw else (section_heading or "الخدمة")
            questions.append(f"ما هي شروط {topic}؟")
            questions.append(f"ما هي متطلبات {topic}؟")

        # Q6: Policy/rule detection
        if re.search(r"(?:سياسة|لائحة|نظام|قرار|قاعدة|ضابط)", chunk_text):
            if kw:
                questions.append(f"ما هي سياسة {kw[0]}؟")

        # Q7: Price/cost detection
        if re.search(r"(?:سعر|تكلفة|رسوم|قيمة|مبلغ|ريال|درهم|دولار)", chunk_text):
            topic = kw[0] if kw else (section_heading or "الخدمة")
            questions.append(f"كم تكلفة {topic}؟")
            questions.append(f"ما هي رسوم {topic}؟")

        # Q8: Contact/support detection
        if re.search(r"(?:تواصل|اتصال|دعم|خدمة عملاء|بريد|هاتف)", chunk_text):
            questions.append("كيف أتواصل مع الدعم؟")
            questions.append("ما هي طرق التواصل؟")

        # Q9: Cancellation/renewal
        if re.search(r"(?:إلغاء|إنهاء|فسخ)", chunk_text):
            topic = kw[0] if kw else "الاشتراك"
            questions.append(f"كيف يمكنني إلغاء {topic}؟")
        if re.search(r"(?:تجديد|تمديد|استمرار)", chunk_text):
            topic = kw[0] if kw else "الاشتراك"
            questions.append(f"كيف أجدد {topic}؟")

    # ── English templates ─────────────────────────────────────────────────
    if lang in ("en", "mixed"):

        if kw:
            questions.append(f"What is {kw[0]}?")
        if len(kw) > 1:
            questions.append(f"How does {kw[1]} work?")

        if section_heading and lang == "en":
            questions.append(f"What are the {section_heading}?")

        if re.search(r"(?:step|steps|procedure|process|how to)", text_lower):
            topic = kw[0] if kw else (section_heading or "the process")
            questions.append(f"What are the steps for {topic}?")
            questions.append(f"How to {topic}?")

        if re.search(r"(?:require|requirement|must|should|prerequisite|condition)", text_lower):
            topic = kw[0] if kw else (section_heading or "this service")
            questions.append(f"What are the requirements for {topic}?")

        if re.search(r"(?:price|cost|fee|charge|rate|amount|pay)", text_lower):
            topic = kw[0] if kw else (section_heading or "the service")
            questions.append(f"How much does {topic} cost?")
            questions.append(f"What are the fees for {topic}?")

        if re.search(r"(?:cancel|terminate|stop|discontinue)", text_lower):
            questions.append("How can I cancel my subscription?")

        if re.search(r"(?:contact|support|help|reach|call)", text_lower):
            questions.append("How do I contact support?")

    # Deduplicate and trim
    seen: set[str] = set()
    unique: list[str] = []
    for q in questions:
        q_norm = q.strip()
        if q_norm and q_norm not in seen:
            seen.add(q_norm)
            unique.append(q_norm)

    return unique[:6]


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5c: ENTITY EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_entities(text: str) -> dict:
    entities: dict = {}

    # Organizations
    orgs = []
    for prefix in ORG_PREFIXES:
        for m in re.findall(rf"{prefix}\s+[\u0600-\u06ff\s]{{2,30}}", text):
            m = m.strip()
            if m not in orgs:
                orgs.append(m)
    if orgs:
        entities["organizations"] = orgs[:10]

    # Dates
    date_pats = [
        r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}",
        r"\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}",
        r"(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+\d{4}",
    ]
    dates = []
    for p in date_pats:
        for m in re.findall(p, text):
            if m not in dates:
                dates.append(m)
    if dates:
        entities["dates"] = dates[:10]

    # Monetary amounts
    amounts = list(set(re.findall(
        r"(?:\d[\d,\.]+)\s*(?:ريال|درهم|دولار|جنيه|SAR|AED|USD|EUR|KWD|BHD|QAR|OMR)",
        text, re.IGNORECASE
    )))
    if amounts:
        entities["amounts"] = amounts[:8]

    # Emails
    emails = list(set(re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)))
    if emails:
        entities["emails"] = emails[:5]

    # Phones
    phones = re.findall(r"(?:\+?\d[\d\s\-]{7,14}\d)", text)
    cleaned = list({p.strip() for p in phones if len(re.sub(r"\D", "", p)) >= 7})
    if cleaned:
        entities["phones"] = cleaned[:5]

    # Percentages
    pcts = list(set(re.findall(r"\d+(?:\.\d+)?%", text)))
    if pcts:
        entities["percentages"] = pcts[:8]

    return entities


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5d: FACT EXTRACTION (improved — wider coverage)
# ══════════════════════════════════════════════════════════════════════════════

def extract_facts(text: str, sections: list) -> list:
    """
    Extract key assertive statements.
    Improved: samples from across the document, not just first sentences.
    """
    facts: list[str] = []
    seen: set[str] = set()

    def _add(sent: str) -> None:
        sent = sent.strip()
        if len(sent) >= 30 and sent not in seen:
            facts.append(sent)
            seen.add(sent)

    # From sections (first + last assertive sentence)
    for sec in sections:
        sec_text = sec.get("text", "")
        sents = re.split(r"[.!?؟]\s+", sec_text)
        if sents:
            _add(sents[0])
        if len(sents) > 2:
            _add(sents[-1])

    # From paragraphs (sample every 3rd paragraph)
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    for i, para in enumerate(paras):
        if i % 3 == 0 or i < 5:
            sents = re.split(r"[.!?؟]\s+", para)
            for sent in sents[:1]:
                _add(sent)
        if len(facts) >= 20:
            break

    return facts[:20]


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5e: INTENT DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_intent(doc_type: str, text: str, keywords: list) -> str:
    kw_terms = {k["term"] for k in keywords}
    policy_sigs  = {"سياسه", "سياسة", "لائحه", "لائحة", "نظام", "قرار", "تعليمات", "قواعد", "اشتراطات", "ضوابط", "policy", "regulation", "compliance", "rule"}
    proc_sigs    = {"خطوات", "كيفيه", "كيفية", "اجراء", "إجراء", "طريقه", "طريقة", "مرحله", "مرحلة", "steps", "how", "procedure", "process"}
    contract_sigs = {"عقد", "اتفاقيه", "اتفاقية", "بنود", "التزام", "contract", "agreement", "clause", "terms"}
    faq_sigs     = {"سؤال", "جواب", "إجابه", "إجابة", "فاق", "faq", "frequently"}

    if doc_type in ("policy",) or kw_terms & policy_sigs:
        return "policy"
    if doc_type in ("procedure",) or kw_terms & proc_sigs:
        return "procedural"
    if doc_type == "faq" or kw_terms & faq_sigs or text.count("؟") + text.count("?") > 5:
        return "faq"
    if doc_type == "contract" or kw_terms & contract_sigs:
        return "contract"
    num_density = len(re.findall(r"\d+", text)) / max(len(text.split()), 1)
    if doc_type in ("excel", "csv") or num_density > 0.12:
        return "reference"
    return "informational"


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 6: QUERY EXPANSION
# ══════════════════════════════════════════════════════════════════════════════

def expand_query(query: str) -> str:
    """
    Expand query with synonyms and normalize Arabic.
    Returns an expanded query string with original + synonym terms.
    """
    # Normalize Arabic
    q = re.sub(r"[إأآ]", "ا", query)
    q = re.sub(r"ة\b", "ه", q)

    # Remove question prefixes (turn questions into keyword queries)
    q = re.sub(r"^(?:ماذا|ما هو|ما هي|ما هي|كيف يمكنني|هل يمكن|هل|متى|أين|كم)\s+", "", q, flags=re.IGNORECASE)
    q = re.sub(r"^(?:what is|what are|how to|how do|when is|where is|can i|is there)\s+", "", q, flags=re.IGNORECASE)

    # Tokenize original query
    words = re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", q.lower())
    extra_terms: list[str] = []

    for word in words:
        # Arabic synonyms
        if word in ARABIC_SYNONYMS:
            extra_terms.extend(ARABIC_SYNONYMS[word][:2])
        # English synonyms
        if word in ENGLISH_SYNONYMS:
            extra_terms.extend(ENGLISH_SYNONYMS[word][:2])

    if extra_terms:
        return q + " " + " ".join(extra_terms)
    return q


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 7: BM25 SCORING
# ══════════════════════════════════════════════════════════════════════════════

def compute_bm25(
    query_terms: set[str],
    doc_term_freq: Counter,
    doc_len: int,
    avg_doc_len: float,
    df: Counter,
    N: int,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """
    Standard BM25 formula.
    Handles term saturation (k1) and document length normalization (b).
    """
    score = 0.0
    if avg_doc_len == 0 or N == 0:
        return 0.0
    for term in query_terms:
        tf = doc_term_freq.get(term, 0)
        if tf == 0:
            continue
        n_docs_with_term = df.get(term, 0)
        idf = math.log((N - n_docs_with_term + 0.5) / (n_docs_with_term + 0.5) + 1)
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))
        score += idf * tf_norm
    return score


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 8: CONFIDENCE SCORING
# ══════════════════════════════════════════════════════════════════════════════

def compute_confidence(score: float, max_score: float) -> dict:
    """
    Normalize score to 0–1 and assign confidence level.
    Levels: HIGH (≥0.65), MEDIUM (0.35–0.65), LOW (<0.35)
    """
    if max_score <= 0:
        normalized = 0.0
    else:
        normalized = min(score / max_score, 1.0)

    if normalized >= 0.65:
        level = "HIGH"
    elif normalized >= 0.35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {"score": round(normalized, 3), "level": level}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def build_training_json(doc) -> str:
    """
    Full RAG pipeline v3.0:
      Clean → Lang Detect → Section Detect → Semantic Chunk (with overlap)
      → Per-chunk: Keywords + Questions
      → Document-level: Entities + Facts + Intent
      → Structured JSON
    """
    raw_text = doc.content or ""

    # Stage 1: Clean
    cleaned = clean_text(raw_text)

    # Stage 2: Language
    lang = detect_language(cleaned)

    # Stage 3: Sections
    sections = detect_sections(cleaned)

    # Stage 4: Semantic chunks with overlap
    chunks = semantic_chunk_with_overlap(cleaned, sections)

    # Stage 5a+5b: Per-chunk enrichment (keywords + questions)
    enriched_chunks = []
    for chunk in chunks:
        chunk_kw = extract_keywords(chunk["text"], top_n=12)
        chunk_qs = generate_questions(
            chunk["text"],
            chunk.get("section_heading"),
            lang,
            chunk_kw,
        )
        chunk["keywords"] = chunk_kw
        chunk["questions"] = chunk_qs
        enriched_chunks.append(chunk)

    # Stage 5c: Document-level knowledge
    doc_keywords = extract_keywords(cleaned, top_n=30)
    entities = extract_entities(cleaned)
    facts = extract_facts(cleaned, sections)
    doc_type_str = str(doc.doc_type.value) if doc.doc_type else "other"
    intent = detect_intent(doc_type_str, cleaned, doc_keywords)

    # Stats
    words = cleaned.split()
    paragraphs = [p for p in cleaned.split("\n\n") if p.strip()]
    total_questions = sum(len(c.get("questions", [])) for c in enriched_chunks)

    structured = {
        "document": {
            "title":       doc.title or "",
            "title_ar":    doc.title_ar or "",
            "type":        doc_type_str,
            "category":    (doc.category.name_ar or doc.category.name) if doc.category else None,
            "version":     doc.version or "1.0",
            "source_file": doc.file_name or None,
            "summary":     doc.summary or None,
        },
        "language": lang,
        "intent":   intent,
        "content":  cleaned,
        "sections": sections if sections else None,
        "chunks":   enriched_chunks,
        "knowledge": {
            "facts":    facts,
            "entities": entities,
            "keywords": doc_keywords,
        },
        "stats": {
            "char_count":       len(cleaned),
            "word_count":       len(words),
            "paragraph_count":  len(paragraphs),
            "section_count":    len(sections),
            "chunk_count":      len(enriched_chunks),
            "keyword_count":    len(doc_keywords),
            "fact_count":       len(facts),
            "question_count":   total_questions,
        },
        "pipeline": {
            "version": PIPELINE_VERSION,
            "stages": [
                "text_cleaning",
                "language_detection",
                "section_detection",
                "semantic_chunking_with_overlap",
                "per_chunk_keyword_extraction",
                "per_chunk_question_generation",
                "entity_extraction",
                "fact_extraction",
                "intent_classification",
            ],
            "processed_at": datetime.utcnow().isoformat(),
        },
        "trained_at": datetime.utcnow().isoformat(),
    }

    return json.dumps(structured, ensure_ascii=False, indent=2)


def build_chunks_for_db(doc, training_json: str) -> list[dict]:
    """
    Extract per-chunk data from training JSON for storage in knowledge_chunks table.
    Returns list of dicts ready to insert as KnowledgeChunk rows.
    """
    try:
        data = json.loads(training_json)
    except Exception:
        return []

    chunks_data = []
    for chunk in data.get("chunks", []):
        # Compute importance: earlier chunks + longer chunks get a small boost
        position = chunk.get("id", 1)
        word_count = chunk.get("words", 0)
        importance = round(
            1.0
            + max(0.0, 0.3 - position * 0.02)     # position bonus (first chunks)
            + min(0.2, word_count / 500.0),         # length bonus
            3
        )
        chunks_data.append({
            "document_id":     doc.id,
            "chunk_index":     chunk.get("id", position),
            "text":            chunk.get("text", ""),
            "keywords":        chunk.get("keywords", []),
            "questions":       chunk.get("questions", []),
            "section_heading": chunk.get("section_heading"),
            "char_count":      chunk.get("chars", 0),
            "word_count":      chunk.get("words", 0),
            "importance_score": importance,
        })
    return chunks_data


# ══════════════════════════════════════════════════════════════════════════════
# RAG SEARCH — REDESIGNED (BM25 + Question Match + Reranking + Confidence)
# ══════════════════════════════════════════════════════════════════════════════

def rag_search(query: str, documents: list, top_k: int = 5, db=None) -> list:
    """
    Hybrid RAG search v3.0
    ─────────────────────────────────────────────────────────────────
    1. Query expansion  — synonyms + normalization
    2. Chunk-level BM25 — proper term saturation & length normalization
    3. Question match   — bonus for chunks whose generated Qs match query
    4. Keyword bonus    — chunk-level keyword overlap
    5. Title/heading bonus
    6. Per-document deduplication — best chunk per doc wins
    7. Confidence scoring — normalized 0–1 + level (HIGH/MEDIUM/LOW)
    ─────────────────────────────────────────────────────────────────
    """
    if not query or not documents:
        return []

    # ── Step 1: Query expansion ───────────────────────────────────────────
    expanded = expand_query(query)
    query_terms = tokenize(expanded)
    if not query_terms:
        query_terms = tokenize(query)   # fallback to raw if expansion emptied it

    # ── Step 2: Load chunks ───────────────────────────────────────────────
    candidate_chunks: list[dict] = []

    for doc in documents:
        if not doc.content:
            continue

        # Try DB-stored chunks first (from knowledge_chunks table)
        db_chunks = []
        if db is not None:
            try:
                from app.domains.knowledge.models import KnowledgeChunk
                db_chunks = (
                    db.query(KnowledgeChunk)
                    .filter(KnowledgeChunk.document_id == doc.id)
                    .order_by(KnowledgeChunk.chunk_index)
                    .all()
                )
            except Exception:
                db_chunks = []

        if db_chunks:
            for ch in db_chunks:
                candidate_chunks.append({
                    "doc":             doc,
                    "chunk_db_id":     ch.id,
                    "text":            ch.text or "",
                    "keywords":        [k["term"] for k in (ch.keywords or [])],
                    "questions":       ch.questions or [],
                    "section_heading": ch.section_heading,
                    "position":        ch.chunk_index,
                    "importance":      ch.importance_score or 1.0,
                })
        else:
            # Fallback: inline chunks from training JSON
            try:
                data = json.loads(doc.content)
                doc_kw = [k["term"] for k in data.get("knowledge", {}).get("keywords", [])]
                for chunk in data.get("chunks", []):
                    candidate_chunks.append({
                        "doc":             doc,
                        "chunk_db_id":     None,
                        "text":            chunk.get("text", ""),
                        "keywords":        [k["term"] for k in chunk.get("keywords", doc_kw)],
                        "questions":       chunk.get("questions", []),
                        "section_heading": chunk.get("section_heading"),
                        "position":        chunk.get("id", 1),
                        "importance":      1.0,
                    })
            except Exception:
                # Last resort: raw text search
                raw = doc.content or ""
                raw_words = tokenize(raw)
                score = len(query_terms & raw_words)
                if score > 0:
                    candidate_chunks.append({
                        "doc":             doc,
                        "chunk_db_id":     None,
                        "text":            raw[:500],
                        "keywords":        list(raw_words)[:15],
                        "questions":       [],
                        "section_heading": None,
                        "position":        1,
                        "importance":      1.0,
                    })

    if not candidate_chunks:
        return []

    # ── Step 3: BM25 corpus statistics ───────────────────────────────────
    N = len(candidate_chunks)
    chunk_term_freqs = [tokenize_with_freq(c["text"]) for c in candidate_chunks]
    doc_lens = [sum(tf.values()) for tf in chunk_term_freqs]
    avg_len = sum(doc_lens) / N if N > 0 else 1.0

    df: Counter = Counter()
    for tf in chunk_term_freqs:
        for term in query_terms:
            if term in tf:
                df[term] += 1

    # ── Step 4: Score each chunk ──────────────────────────────────────────
    scored: list[dict] = []
    for i, chunk in enumerate(candidate_chunks):
        # BM25
        bm25 = compute_bm25(query_terms, chunk_term_freqs[i], doc_lens[i], avg_len, df, N)

        # Question match bonus — highest-value signal for semantic queries
        q_bonus = 0.0
        matched_qs: list[str] = []
        for q in chunk.get("questions", []):
            q_terms = tokenize(q)
            overlap = len(query_terms & q_terms)
            if overlap > 0:
                # More overlap = higher bonus (capped at 4.0 per question)
                q_bonus += min(overlap * 1.5, 4.0)
                matched_qs.append(q)

        # Chunk keyword match bonus
        kw_overlap = len(query_terms & set(chunk.get("keywords", [])))
        kw_bonus = kw_overlap * 1.2

        # Section heading match
        heading_bonus = 0.0
        if chunk.get("section_heading"):
            h_terms = tokenize(chunk["section_heading"])
            heading_bonus = len(query_terms & h_terms) * 2.0

        # Document title match
        title_text = (chunk["doc"].title_ar or chunk["doc"].title or "")
        title_terms = tokenize(title_text)
        title_bonus = len(query_terms & title_terms) * 3.0

        # Position bonus (first 3 chunks slightly preferred)
        pos = chunk.get("position", 1)
        position_bonus = max(0.0, 0.4 - pos * 0.03)

        # Importance weight
        importance_bonus = (chunk.get("importance", 1.0) - 1.0) * 0.5

        total = bm25 + q_bonus + kw_bonus + heading_bonus + title_bonus + position_bonus + importance_bonus

        if total > 0:
            scored.append({
                "chunk":       chunk,
                "score":       total,
                "bm25":        bm25,
                "q_bonus":     q_bonus,
                "matched_qs":  matched_qs,
            })

    if not scored:
        return []

    # ── Step 5: Sort and deduplicate by document ──────────────────────────
    scored.sort(key=lambda x: x["score"], reverse=True)
    max_score = scored[0]["score"] if scored else 1.0

    seen_docs: set[int] = set()
    results: list[dict] = []

    for item in scored:
        doc = item["chunk"]["doc"]
        if doc.id in seen_docs:
            continue
        seen_docs.add(doc.id)

        # Confidence
        conf = compute_confidence(item["score"], max_score)

        # Enrich with document-level metadata from JSON
        intent = None
        lang = None
        chunk_count = 0
        try:
            data = json.loads(doc.content or "{}")
            intent = data.get("intent")
            lang = data.get("language")
            chunk_count = data.get("stats", {}).get("chunk_count", 0)
        except Exception:
            pass

        results.append({
            "doc_id":           doc.id,
            "title":            doc.title_ar or doc.title,
            "score":            round(item["score"], 3),
            "bm25_score":       round(item["bm25"], 3),
            "confidence":       conf["level"],
            "confidence_score": conf["score"],
            "excerpt":          item["chunk"]["text"][:450],
            "section":          item["chunk"].get("section_heading"),
            "matched_questions": item["matched_qs"][:3],
            "intent":           intent,
            "language":         lang,
            "chunk_count":      chunk_count,
            "matched_type":     (
                "question" if item["q_bonus"] > item["bm25"]
                else "bm25" if item["bm25"] > 0
                else "keyword"
            ),
        })

        if len(results) >= top_k:
            break

    return results
