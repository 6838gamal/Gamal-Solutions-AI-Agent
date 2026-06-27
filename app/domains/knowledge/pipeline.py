"""
RAG Data Pipeline — Production-grade knowledge processing system.
Stages: Clean → Language Detection → Section Detection → Semantic Chunking
        → Knowledge Extraction (Facts, Entities, Keywords, Intent) → JSON Build
"""
import re
import json
import math
import logging
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Stop Words ───────────────────────────────────────────────────────────────

ARABIC_STOP = {
    "من", "في", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "تلك",
    "التي", "الذي", "ما", "أن", "كان", "كانت", "يكون", "تكون", "قد",
    "لم", "لن", "لا", "إن", "إذا", "عند", "بعد", "قبل", "أو", "و",
    "ثم", "حتى", "كما", "أيضاً", "أيضا", "هو", "هي", "هم", "هن",
    "أنت", "أنا", "نحن", "أنتم", "يتم", "تم", "كل", "بعض", "غير",
    "حول", "خلال", "ضمن", "أكثر", "أقل", "جداً", "جدا", "وفق",
    "وفقاً", "حيث", "به", "بها", "لها", "له", "بهم", "لهم", "منه",
    "منها", "هناك", "هنا", "أمام", "خلف", "فوق", "تحت", "عبر",
    "خلاله", "خلالها", "ذلك", "هذا", "هذه", "تلك", "ولا", "وما",
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
}

STOP_WORDS = ARABIC_STOP | ENGLISH_STOP

ORG_PREFIXES = [
    "شركة", "مؤسسة", "هيئة", "وزارة", "مجلس", "لجنة", "مركز",
    "إدارة", "دائرة", "جمعية", "بنك", "صندوق", "جهاز", "منظمة",
]


# ── Stage 1: Clean ────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Remove invisible/control characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0]", " ", text)
    text = re.sub(r"[\r\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize Arabic characters
    text = re.sub(r"[إأآ]", "ا", text)
    # Normalize whitespace (keep newlines for structure)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove repeated punctuation
    text = re.sub(r"\.{3,}", "...", text)
    text = re.sub(r"-{3,}", "—", text)
    return text.strip()


# ── Stage 2: Language Detection ───────────────────────────────────────────────

def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[\u0600-\u06ff]", text))
    english = len(re.findall(r"[a-zA-Z]", text))
    if arabic > english * 1.5:
        return "ar"
    if english > arabic * 1.5:
        return "en"
    return "mixed"


# ── Stage 3: Section Detection ────────────────────────────────────────────────

def detect_sections(text: str) -> list:
    lines = text.split("\n")
    sections = []
    current = {"heading": None, "text": []}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        is_heading = (
            len(line) < 120 and (
                line.endswith(":") or
                line.endswith("：") or
                (line.isupper() and 2 <= len(line.split()) <= 8) or
                line.startswith("#") or
                bool(re.match(r"^(?:\d+[\.\-\)]\s+[^\d]|\b[أ-ي][\.\-\)]\s+)", line))
            )
        )
        if is_heading:
            if current["text"]:
                sections.append(current)
            current = {
                "heading": re.sub(r"^#+\s*", "", line).strip(": ："),
                "text": [],
            }
        else:
            current["text"].append(line)
    if current["text"] or current["heading"]:
        sections.append(current)

    return [
        {"heading": s["heading"], "text": " ".join(s["text"])}
        for s in sections
        if s["text"]
    ]


# ── Stage 4: Semantic Chunking ────────────────────────────────────────────────

def semantic_chunk(text: str, max_chars: int = 700, min_chars: int = 60) -> list:
    if not text:
        return []

    chunks = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    buffer = []
    buf_len = 0

    def flush(buf):
        joined = " ".join(buf)
        if len(joined) >= min_chars:
            chunks.append(joined)

    for para in paragraphs:
        if len(para) > max_chars:
            if buffer:
                flush(buffer)
                buffer, buf_len = [], 0
            # Split large paragraph on sentence boundaries
            sentences = re.split(r"(?<=[.!?؟،])\s+", para)
            sb, sl = [], 0
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if sl + len(sent) > max_chars and sb:
                    flush(sb)
                    sb, sl = [sent], len(sent)
                else:
                    sb.append(sent)
                    sl += len(sent)
            if sb:
                flush(sb)
        elif buf_len + len(para) > max_chars:
            if buffer:
                flush(buffer)
            buffer, buf_len = [para], len(para)
        else:
            buffer.append(para)
            buf_len += len(para)

    if buffer:
        flush(buffer)

    return [
        {
            "id": i + 1,
            "text": c,
            "chars": len(c),
            "words": len(c.split()),
        }
        for i, c in enumerate(chunks)
    ]


# ── Stage 5: Knowledge Extraction ─────────────────────────────────────────────

def extract_keywords(text: str, top_n: int = 25) -> list:
    words = re.findall(r"[\u0600-\u06ff]{3,}|[a-zA-Z]{4,}", text.lower())
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
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def extract_entities(text: str) -> dict:
    entities: dict = {}

    # Arabic organizations
    orgs = []
    for prefix in ORG_PREFIXES:
        matches = re.findall(rf"{prefix}\s+[\u0600-\u06ff\s]{{2,30}}", text)
        for m in matches:
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
    cleaned_phones = list({p.strip() for p in phones if len(re.sub(r"\D", "", p)) >= 7})
    if cleaned_phones:
        entities["phones"] = cleaned_phones[:5]

    return entities


def extract_facts(text: str, sections: list) -> list:
    facts = []
    seen: set = set()

    # First assertive sentence from each section
    for sec in sections:
        sec_text = sec.get("text", "")
        sentences = re.split(r"[.!?؟]\s+", sec_text)
        for sent in sentences[:2]:
            sent = sent.strip()
            if len(sent) >= 35 and sent not in seen:
                facts.append(sent)
                seen.add(sent)
                break

    # Fill from paragraphs if needed
    if len(facts) < 8:
        for para in [p.strip() for p in text.split("\n\n") if p.strip()][:25]:
            sentences = re.split(r"[.!?؟]\s+", para)
            for sent in sentences[:1]:
                sent = sent.strip()
                if len(sent) >= 45 and sent not in seen:
                    facts.append(sent)
                    seen.add(sent)
                    break
            if len(facts) >= 15:
                break

    return facts[:15]


def detect_intent(doc_type: str, text: str, keywords: list) -> str:
    kw_terms = {k["term"] for k in keywords}
    policy_signals = {"سياسة", "لائحة", "نظام", "قرار", "تعليمات", "قواعد", "اشتراطات", "ضوابط", "policy", "regulation", "compliance"}
    proc_signals = {"خطوات", "كيفية", "إجراء", "طريقة", "مرحلة", "steps", "how", "procedure", "process"}
    contract_signals = {"عقد", "اتفاقية", "بنود", "التزام", "contract", "agreement", "clause"}

    if doc_type in ("policy",) or kw_terms & policy_signals:
        return "policy"
    if doc_type in ("procedure",) or kw_terms & proc_signals:
        return "procedural"
    if doc_type == "faq" or text.count("؟") + text.count("?") > 5:
        return "faq"
    if doc_type == "contract" or kw_terms & contract_signals:
        return "contract"
    number_density = len(re.findall(r"\d+", text)) / max(len(text.split()), 1)
    if doc_type in ("excel", "csv") or number_density > 0.12:
        return "reference"
    return "informational"


# ── Main Pipeline Entry Point ──────────────────────────────────────────────────

def build_training_json(doc) -> str:
    """
    Full RAG pipeline:
      Clean → Lang Detect → Section Detect → Semantic Chunk
      → Knowledge Extract (Facts, Entities, Keywords, Intent) → JSON
    Returns a structured, clean JSON string ready for storage and RAG retrieval.
    """
    raw_text = doc.content or ""

    # Stage 1: Clean
    cleaned = clean_text(raw_text)

    # Stage 2: Language
    lang = detect_language(cleaned)

    # Stage 3: Sections
    sections = detect_sections(cleaned)

    # Stage 4: Semantic chunks
    chunks = semantic_chunk(cleaned)

    # Stage 5: Knowledge extraction
    keywords = extract_keywords(cleaned, top_n=25)
    entities = extract_entities(cleaned)
    facts = extract_facts(cleaned, sections)
    doc_type_str = str(doc.doc_type.value) if doc.doc_type else "other"
    intent = detect_intent(doc_type_str, cleaned, keywords)

    # Stats
    words = cleaned.split()
    paragraphs = [p for p in cleaned.split("\n\n") if p.strip()]

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
        "chunks": chunks,
        "knowledge": {
            "facts":    facts,
            "entities": entities,
            "keywords": keywords,
        },
        "stats": {
            "char_count":      len(cleaned),
            "word_count":      len(words),
            "paragraph_count": len(paragraphs),
            "section_count":   len(sections),
            "chunk_count":     len(chunks),
            "keyword_count":   len(keywords),
            "fact_count":      len(facts),
        },
        "pipeline": {
            "version": "2.0",
            "stages": [
                "text_cleaning",
                "language_detection",
                "section_detection",
                "semantic_chunking",
                "keyword_extraction",
                "entity_extraction",
                "fact_extraction",
                "intent_classification",
            ],
            "processed_at": datetime.utcnow().isoformat(),
        },
        "trained_at": datetime.utcnow().isoformat(),
    }

    return json.dumps(structured, ensure_ascii=False, indent=2)


def rag_search(query: str, documents: list, top_k: int = 5) -> list:
    """
    Hybrid search: keyword overlap + fact/content matching.
    Returns top_k ranked results from trained documents.
    """
    query_lower = query.lower()
    query_words = set(re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", query_lower))
    query_words -= STOP_WORDS

    results = []
    for doc in documents:
        if not doc.content:
            continue
        try:
            data = json.loads(doc.content)
        except Exception:
            # Fallback: plain text search
            score = sum(1 for w in query_words if w in (doc.content or "").lower())
            if score > 0:
                results.append({
                    "doc_id": doc.id,
                    "title":  doc.title_ar or doc.title,
                    "score":  score,
                    "matched_type": "text",
                    "excerpt": (doc.content or "")[:300],
                    "intent": None,
                    "language": None,
                })
            continue

        score = 0.0
        matched_type = "none"
        excerpt = ""

        # Keyword match against extracted keywords
        doc_kw = {k["term"] for k in data.get("knowledge", {}).get("keywords", [])}
        kw_overlap = len(query_words & doc_kw)
        score += kw_overlap * 3.0

        # Match against facts
        facts = data.get("knowledge", {}).get("facts", [])
        for fact in facts:
            fact_words = set(re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", fact.lower()))
            overlap = len(query_words & (fact_words - STOP_WORDS))
            if overlap > 0:
                score += overlap * 2.0
                if not excerpt:
                    excerpt = fact
                matched_type = "fact"

        # Match against chunks
        best_chunk_score = 0
        best_chunk = ""
        for chunk in data.get("chunks", []):
            chunk_text = chunk.get("text", "")
            chunk_words = set(re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", chunk_text.lower()))
            overlap = len(query_words & (chunk_words - STOP_WORDS))
            if overlap > best_chunk_score:
                best_chunk_score = overlap
                best_chunk = chunk_text
        score += best_chunk_score * 1.5
        if best_chunk and not excerpt:
            excerpt = best_chunk[:300]
            matched_type = "chunk"

        # Title match (high weight)
        title_words = set(re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", (doc.title_ar or doc.title or "").lower()))
        title_overlap = len(query_words & title_words)
        score += title_overlap * 4.0
        if title_overlap:
            matched_type = "title"

        if score > 0:
            results.append({
                "doc_id":       doc.id,
                "title":        doc.title_ar or doc.title,
                "score":        round(score, 2),
                "matched_type": matched_type,
                "excerpt":      excerpt[:350] if excerpt else (data.get("content", "")[:350]),
                "intent":       data.get("intent"),
                "language":     data.get("language"),
                "chunk_count":  data.get("stats", {}).get("chunk_count", 0),
                "fact_count":   data.get("stats", {}).get("fact_count", 0),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
