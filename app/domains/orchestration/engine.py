"""
Enterprise Knowledge Routing & Agent Orchestration Engine
═══════════════════════════════════════════════════════════

Architecture:
  Query
    ↓
  [1] Query Expansion        (synonyms + normalization)
    ↓
  [2] Domain Classification  (signal-based → primary + secondary domains)
    ↓
  [3] Agent Selection        (find best matching active agent per domain)
    ↓
  [4] Domain-Filtered RAG    (BM25 chunk search filtered to relevant docs)
    ↓
  [5] Result Aggregation     (merge + deduplicate cross-agent results)
    ↓
  [6] Confidence Gate        (LOW → log KnowledgeGap)
    ↓
  Structured Response with routing metadata + citations
"""
import re
import logging
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN SIGNAL DICTIONARY
# Each domain has keyword signals in Arabic + English, and a base weight.
# ══════════════════════════════════════════════════════════════════════════════

DOMAIN_SIGNALS: dict[str, dict] = {
    "customer_support": {
        "ar": {
            "مشكله", "مشكلة", "شكوى", "شكوه", "دعم", "مساعده", "مساعدة",
            "استفسار", "تذكره", "تذكرة", "خطأ", "عطل", "إصلاح", "رجوع",
            "استرداد", "إلغاء", "تعطل", "لا يعمل", "مشكلتي", "لا أستطيع",
            "غير قادر", "توقف", "انقطع", "فشل", "رد", "شكل", "أريد إلغاء",
        },
        "en": {
            "problem", "issue", "complaint", "support", "help", "error", "bug",
            "ticket", "broken", "fix", "refund", "return", "cancel", "not working",
            "failed", "unable", "cannot", "stopped", "disconnected", "troubleshoot",
        },
        "weight": 1.0,
    },
    "sales": {
        "ar": {
            "سعر", "تكلفه", "تكلفة", "اشتراك", "شراء", "عرض", "خصم",
            "ترقيه", "ترقية", "باقه", "باقة", "خطه", "خطة", "بيع", "عقد",
            "اقتراح", "توصيه", "توصية", "منتج", "خدمه", "خدمة", "تجربه",
            "تجربة", "كيف أشتري", "أريد أشتري", "هل يوجد عرض",
        },
        "en": {
            "price", "cost", "buy", "purchase", "subscription", "plan", "offer",
            "discount", "upgrade", "deal", "contract", "quote", "proposal",
            "sell", "revenue", "product", "service", "trial", "demo",
            "how to buy", "pricing", "fee", "package",
        },
        "weight": 1.0,
    },
    "market_intel": {
        "ar": {
            "منافس", "منافسين", "سوق", "اتجاه", "اتجاهات", "تحليل",
            "فرصه", "فرصة", "فرص", "بيانات", "إحصاء", "تقرير", "دراسه",
            "دراسة", "صناعه", "صناعة", "ابتكار", "توقعات", "بحث",
            "ديموغرافيك", "حصه سوقيه", "حصة سوقية", "ترند",
        },
        "en": {
            "market", "competitor", "trend", "analysis", "opportunity", "data",
            "statistics", "report", "benchmark", "industry", "research",
            "forecast", "segment", "demographic", "market share", "landscape",
            "insights", "intelligence",
        },
        "weight": 1.0,
    },
    "hr": {
        "ar": {
            "موظف", "موظفين", "توظيف", "إجازه", "إجازة", "راتب", "رواتب",
            "أداء", "تدريب", "تقييم", "تعيين", "استقاله", "استقالة",
            "موارد بشريه", "موارد بشرية", "عقد عمل", "بيئه عمل",
        },
        "en": {
            "employee", "hire", "leave", "salary", "performance", "training",
            "hr", "human resources", "recruitment", "payroll", "resignation",
            "onboarding", "benefits", "vacation", "appraisal",
        },
        "weight": 0.9,
    },
    "finance": {
        "ar": {
            "ميزانيه", "ميزانية", "مالي", "ماليه", "مالية", "فاتوره",
            "فاتورة", "دفع", "سداد", "حسابات", "إيرادات", "مصروفات",
            "ربح", "خساره", "خسارة", "تدقيق", "ضريبه", "ضريبة",
        },
        "en": {
            "budget", "financial", "invoice", "payment", "billing", "accounts",
            "revenue", "expense", "profit", "loss", "accounting", "tax",
            "audit", "cashflow", "balance sheet",
        },
        "weight": 0.9,
    },
    "operations": {
        "ar": {
            "عمليات", "إجراءات", "تشغيل", "مشروع", "مهمه", "مهمة",
            "جدول", "مواعيد", "تسليم", "إنتاج", "لوجستيك", "سير عمل",
            "أتمتة", "خطه تشغيليه", "خطة تشغيلية",
        },
        "en": {
            "operations", "process", "procedure", "project", "task", "schedule",
            "delivery", "production", "logistics", "workflow", "execution",
            "automation", "operational", "supply chain",
        },
        "weight": 0.9,
    },
    "general": {
        "ar": set(),
        "en": set(),
        "weight": 0.3,   # fallback — lowest priority
    },
}

# Map agent_type → primary domain
AGENT_TYPE_DOMAIN: dict[str, str] = {
    "customer_service": "customer_support",
    "sales":            "sales",
    "market_intel":     "market_intel",
    "operations":       "operations",
    "hr":               "hr",
    "finance":          "finance",
    "executive":        "general",
    "custom":           "general",
}

# Map domain → preferred agent_type
DOMAIN_AGENT_TYPE: dict[str, str] = {v: k for k, v in AGENT_TYPE_DOMAIN.items()}

# Which knowledge domains each agent type can access (in priority order)
AGENT_KNOWLEDGE_ACCESS: dict[str, list[str]] = {
    "customer_service": ["customer_support", "product", "general"],
    "sales":            ["sales", "product", "customer_support", "general"],
    "market_intel":     ["market_intel", "general"],
    "operations":       ["operations", "general"],
    "hr":               ["hr", "general"],
    "finance":          ["finance", "general"],
    "executive":        ["general", "customer_support", "sales", "market_intel", "operations", "hr", "finance"],
    "custom":           ["general"],
}


# ══════════════════════════════════════════════════════════════════════════════
# TOKENIZER (shared with pipeline)
# ══════════════════════════════════════════════════════════════════════════════

_STOP = {
    "من", "في", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "ما", "أن",
    "the", "a", "an", "is", "are", "was", "to", "of", "in", "on", "at",
    "and", "or", "but", "it", "i", "my", "you", "your", "we", "our",
}


def _tokenize(text: str) -> set[str]:
    text = re.sub(r"[إأآ]", "ا", text.lower())
    words = re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", text)
    return {w for w in words if w not in _STOP}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: DOMAIN CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def classify_domain(query: str) -> dict:
    """
    Classify query into one or more knowledge domains using signal matching.

    Returns:
        {
            "primary_domain": str,
            "secondary_domains": list[str],
            "domain_scores": {domain: score},
            "matched_signals": list[str],
            "confidence": float (0–1),
            "is_multi_domain": bool,
        }
    """
    query_norm = re.sub(r"[إأآ]", "ا", query.lower())
    tokens = _tokenize(query_norm)
    raw_query_words = set(re.findall(r"[\u0600-\u06ff]{2,}|[a-zA-Z]{3,}", query_norm))

    domain_scores: dict[str, float] = {}
    all_matched: list[str] = []

    for domain, config in DOMAIN_SIGNALS.items():
        score = 0.0
        matched: list[str] = []

        ar_signals = config["ar"]
        en_signals = config["en"]
        weight = config["weight"]

        # Token match (single words)
        for token in tokens:
            if token in ar_signals or token in en_signals:
                score += weight
                matched.append(token)

        # Phrase match (bigrams in raw query)
        words_list = list(raw_query_words)
        for i in range(len(words_list) - 1):
            phrase = f"{words_list[i]} {words_list[i+1]}"
            if phrase in ar_signals or phrase in en_signals:
                score += weight * 1.5   # phrase matches score higher
                matched.append(phrase)

        domain_scores[domain] = round(score, 3)
        all_matched.extend(matched)

    # Sort domains by score
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    best_domain, best_score = sorted_domains[0]
    second_domain, second_score = sorted_domains[1] if len(sorted_domains) > 1 else ("general", 0)

    # If no signals matched, fall back to "general"
    if best_score == 0:
        best_domain = "general"
        best_score = 0.1

    # Multi-domain: secondary is relevant if score >= 50% of primary
    secondary_domains = [
        d for d, s in sorted_domains[1:]
        if s > 0 and s >= best_score * 0.5 and d != "general"
    ]

    # Normalize confidence: 0–1 based on how many signals matched
    total_signals = sum(domain_scores.values())
    confidence = round(best_score / total_signals, 3) if total_signals > 0 else 0.3

    return {
        "primary_domain":    best_domain,
        "secondary_domains": secondary_domains[:2],
        "domain_scores":     domain_scores,
        "matched_signals":   list(set(all_matched))[:10],
        "confidence":        min(confidence, 1.0),
        "is_multi_domain":   len(secondary_domains) > 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: AGENT SELECTION
# ══════════════════════════════════════════════════════════════════════════════

def select_agents(routing: dict, available_agents: list) -> list[dict]:
    """
    Given a routing decision and a list of active Agent objects,
    return ordered list of agents to use (primary first, then secondary).
    """
    primary_domain = routing["primary_domain"]
    secondary_domains = routing["secondary_domains"]

    primary_agent_type = DOMAIN_AGENT_TYPE.get(primary_domain, "custom")
    secondary_types = [DOMAIN_AGENT_TYPE.get(d, "custom") for d in secondary_domains]

    selected = []
    seen_ids: set[int] = set()

    # Primary agent
    for agent in available_agents:
        atype = str(agent.agent_type.value if hasattr(agent.agent_type, "value") else agent.agent_type)
        if atype == primary_agent_type and agent.id not in seen_ids:
            selected.append({"agent": agent, "role": "primary", "domain": primary_domain})
            seen_ids.add(agent.id)
            break

    # Executive as fallback if no primary found
    if not selected:
        for agent in available_agents:
            atype = str(agent.agent_type.value if hasattr(agent.agent_type, "value") else agent.agent_type)
            if atype == "executive" and agent.id not in seen_ids:
                selected.append({"agent": agent, "role": "primary_fallback", "domain": "general"})
                seen_ids.add(agent.id)
                break

    # Secondary agents
    for stype, sdomain in zip(secondary_types, secondary_domains):
        for agent in available_agents:
            atype = str(agent.agent_type.value if hasattr(agent.agent_type, "value") else agent.agent_type)
            if atype == stype and agent.id not in seen_ids:
                selected.append({"agent": agent, "role": "secondary", "domain": sdomain})
                seen_ids.add(agent.id)
                break

    return selected


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4+5: DOMAIN-FILTERED RAG + AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

def _get_docs_for_domains(db, domains: list[str]) -> list:
    """
    Load trained KnowledgeDocuments accessible to the given domains.
    Falls back to all trained docs if domain filtering yields nothing.
    """
    from app.domains.knowledge.models import KnowledgeDocument

    # Try domain-filtered first
    if domains and "general" not in domains:
        domain_docs = (
            db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.is_trained == True,
                KnowledgeDocument.domain.in_(domains + ["general"]),
            )
            .all()
        )
        if domain_docs:
            return domain_docs

    # Fallback: all trained documents
    return (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.is_trained == True)
        .all()
    )


def multi_agent_search(
    query: str,
    db,
    agent_id: int | None = None,
    top_k: int = 5,
    session_id: str | None = None,
) -> dict:
    """
    Full orchestration pipeline:
      classify → select agents → domain-filtered RAG → aggregate → confidence gate

    Returns a structured response dict ready for API serialization.
    """
    from app.domains.knowledge.pipeline import rag_search, expand_query
    from app.domains.agents.models import Agent, AgentStatus
    from app.domains.orchestration.models import AgentRoutingLog, KnowledgeGap

    # ── Step 1: Classify domain ───────────────────────────────────────────
    routing = classify_domain(query)
    primary_domain = routing["primary_domain"]

    # ── Step 2: Select agents ─────────────────────────────────────────────
    active_agents = (
        db.query(Agent)
        .filter(Agent.status == AgentStatus.ACTIVE)
        .all()
    )
    selected = select_agents(routing, active_agents)

    # If caller specified a specific agent, use that as primary
    if agent_id:
        for a in active_agents:
            if a.id == agent_id:
                atype = str(a.agent_type.value if hasattr(a.agent_type, "value") else a.agent_type)
                domain = AGENT_TYPE_DOMAIN.get(atype, "general")
                selected = [{"agent": a, "role": "primary", "domain": domain}]
                routing["primary_domain"] = domain
                primary_domain = domain
                break

    # ── Step 3: Determine knowledge domains to search ─────────────────────
    if selected:
        primary_agent = selected[0]["agent"]
        atype = str(primary_agent.agent_type.value
                    if hasattr(primary_agent.agent_type, "value")
                    else primary_agent.agent_type)
        search_domains = AGENT_KNOWLEDGE_ACCESS.get(atype, ["general"])
    else:
        search_domains = [primary_domain, "general"]

    # ── Step 4: Domain-filtered RAG ───────────────────────────────────────
    docs = _get_docs_for_domains(db, search_domains)
    results = rag_search(query, docs, top_k=top_k, db=db)

    # ── Step 5: Confidence gate → log gaps ───────────────────────────────
    top_confidence = results[0]["confidence"] if results else "NONE"
    top_score = results[0]["score"] if results else 0.0

    if top_confidence in ("LOW", "NONE") or not results:
        # Log knowledge gap for continuous learning
        _log_knowledge_gap(db, query, primary_domain, top_confidence, top_score)

    # ── Step 6: Log routing decision ──────────────────────────────────────
    routed_agent_id = selected[0]["agent"].id if selected else None
    log = AgentRoutingLog(
        query=query,
        primary_domain=primary_domain,
        secondary_domains=routing["secondary_domains"],
        routed_agent_id=routed_agent_id,
        routing_confidence=routing["confidence"],
        domain_scores=routing["domain_scores"],
        matched_signals=routing["matched_signals"],
        retrieval_confidence=top_confidence,
        results_count=len(results),
        session_id=session_id,
    )
    db.add(log)
    db.commit()

    # ── Build response ────────────────────────────────────────────────────
    return {
        "query":          query,
        "expanded_query": expand_query(query),
        "routing": {
            "primary_domain":    routing["primary_domain"],
            "secondary_domains": routing["secondary_domains"],
            "confidence":        routing["confidence"],
            "matched_signals":   routing["matched_signals"],
            "is_multi_domain":   routing["is_multi_domain"],
        },
        "agents_used": [
            {
                "id":     s["agent"].id,
                "name":   s["agent"].name_ar or s["agent"].name,
                "type":   str(s["agent"].agent_type.value
                              if hasattr(s["agent"].agent_type, "value")
                              else s["agent"].agent_type),
                "role":   s["role"],
                "domain": s["domain"],
            }
            for s in selected
        ],
        "knowledge_domains_searched": search_domains,
        "results": results,
        "top_confidence": top_confidence,
        "total_docs_searched": len(docs),
        "needs_knowledge_update": top_confidence in ("LOW", "NONE"),
        "routing_log_id": log.id,
    }


def _log_knowledge_gap(
    db,
    query: str,
    domain: str,
    confidence: str,
    top_score: float,
) -> None:
    """Record or increment a knowledge gap."""
    from app.domains.orchestration.models import KnowledgeGap

    # Check if this exact query was already logged (case-insensitive)
    existing = (
        db.query(KnowledgeGap)
        .filter(KnowledgeGap.query.ilike(query.strip()))
        .first()
    )
    if existing:
        existing.occurrence_count += 1
        existing.last_asked_at = datetime.utcnow()
        db.commit()
        return

    # Suggest action based on domain
    action_map = {
        "customer_support": "أضف وثيقة سياسة دعم العملاء أو قسم الأسئلة الشائعة",
        "sales":            "أضف كتيب المنتجات أو قائمة الأسعار وعروض المبيعات",
        "market_intel":     "أضف تقارير السوق أو ملفات تحليل المنافسين",
        "hr":               "أضف لائحة الموارد البشرية أو سياسات الإجازات",
        "finance":          "أضف السياسات المالية أو قوائم الرسوم",
        "operations":       "أضف إجراءات التشغيل أو دليل العمليات",
        "general":          "أضف وثيقة عامة أو محتوى مناسب لهذا الاستفسار",
    }

    gap = KnowledgeGap(
        query=query.strip(),
        attempted_domain=domain,
        retrieval_confidence=confidence,
        top_score=round(top_score, 3),
        suggested_domain=domain,
        suggested_action=action_map.get(domain, action_map["general"]),
    )
    db.add(gap)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# AGENT HANDOFF
# ══════════════════════════════════════════════════════════════════════════════

def create_handoff(
    db,
    query: str,
    from_agent_id: int | None,
    to_agent_id: int,
    reason: str,
    context: dict | None = None,
) -> int:
    """Create an agent-to-agent handoff record. Returns handoff ID."""
    from app.domains.orchestration.models import AgentHandoff
    handoff = AgentHandoff(
        query=query,
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        reason=reason,
        context=context or {},
    )
    db.add(handoff)
    db.commit()
    db.refresh(handoff)
    return handoff.id


def complete_handoff(db, handoff_id: int, result: str) -> None:
    """Mark a handoff as completed with the final result."""
    from app.domains.orchestration.models import AgentHandoff
    handoff = db.query(AgentHandoff).filter(AgentHandoff.id == handoff_id).first()
    if handoff:
        handoff.status = "completed"
        handoff.result = result
        handoff.completed_at = datetime.utcnow()
        db.commit()
