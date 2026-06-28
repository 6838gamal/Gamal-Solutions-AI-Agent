"""
Orchestration API Endpoints
════════════════════════════
POST /orchestration/ask          — full multi-agent RAG query
POST /orchestration/route        — classify query domain only (no retrieval)
POST /orchestration/handoff      — create agent-to-agent handoff
GET  /orchestration/gaps         — list knowledge gaps (continuous learning)
PUT  /orchestration/gaps/{id}/resolve
GET  /orchestration/routing-logs — routing history
GET  /orchestration/stats        — platform-level analytics
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.auth.models import User

router = APIRouter(prefix="/orchestration", tags=["Orchestration"])


# ── Request / Response schemas ─────────────────────────────────────────────

class AskRequest(BaseModel):
    query: str
    agent_id: int | None = None
    top_k: int = 5
    session_id: str | None = None


class RouteRequest(BaseModel):
    query: str


class HandoffRequest(BaseModel):
    query: str
    from_agent_id: int | None = None
    to_agent_id: int
    reason: str
    context: dict | None = None


class ResolveGapRequest(BaseModel):
    notes: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/ask")
def orchestrated_ask(
    payload: AskRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Full multi-agent RAG pipeline:
      classify domain → select agent → domain-filtered knowledge search → response

    Automatically logs knowledge gaps when confidence is LOW.
    """
    from app.domains.orchestration.engine import multi_agent_search
    result = multi_agent_search(
        query=payload.query,
        db=db,
        agent_id=payload.agent_id,
        top_k=payload.top_k,
        session_id=payload.session_id,
    )
    return result


@router.post("/route")
def classify_query(
    payload: RouteRequest,
    _: User = Depends(get_current_user),
):
    """
    Classify which domain (and agent type) should handle this query.
    No knowledge retrieval — routing analysis only.
    """
    from app.domains.orchestration.engine import classify_domain, DOMAIN_AGENT_TYPE
    routing = classify_domain(payload.query)
    return {
        "query":            payload.query,
        "primary_domain":   routing["primary_domain"],
        "preferred_agent":  DOMAIN_AGENT_TYPE.get(routing["primary_domain"], "custom"),
        "secondary_domains": routing["secondary_domains"],
        "confidence":       routing["confidence"],
        "domain_scores":    routing["domain_scores"],
        "matched_signals":  routing["matched_signals"],
        "is_multi_domain":  routing["is_multi_domain"],
    }


@router.post("/handoff")
def create_agent_handoff(
    payload: HandoffRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Create an agent-to-agent task handoff."""
    from app.domains.orchestration.engine import create_handoff
    handoff_id = create_handoff(
        db=db,
        query=payload.query,
        from_agent_id=payload.from_agent_id,
        to_agent_id=payload.to_agent_id,
        reason=payload.reason,
        context=payload.context,
    )
    return {"message": "تم إنشاء التحويل بين الوكلاء", "handoff_id": handoff_id}


@router.post("/handoff/{handoff_id}/complete")
def complete_agent_handoff(
    handoff_id: int,
    result: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.domains.orchestration.engine import complete_handoff
    complete_handoff(db, handoff_id, result)
    return {"message": "تم إتمام التحويل", "handoff_id": handoff_id}


@router.get("/gaps")
def list_knowledge_gaps(
    skip: int = 0,
    limit: int = 50,
    domain: str | None = Query(None),
    is_resolved: bool | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    List knowledge gaps — queries that returned LOW/no confidence.
    These are signals for what knowledge needs to be added to the system.
    """
    from app.domains.orchestration.models import KnowledgeGap
    q = db.query(KnowledgeGap)
    if domain:
        q = q.filter(KnowledgeGap.attempted_domain == domain)
    if is_resolved is not None:
        q = q.filter(KnowledgeGap.is_resolved == is_resolved)
    gaps = q.order_by(KnowledgeGap.occurrence_count.desc()).offset(skip).limit(limit).all()
    return {
        "total": q.count(),
        "gaps": [
            {
                "id":               g.id,
                "query":            g.query,
                "domain":           g.attempted_domain,
                "confidence":       g.retrieval_confidence,
                "top_score":        g.top_score,
                "suggested_action": g.suggested_action,
                "occurrences":      g.occurrence_count,
                "is_resolved":      g.is_resolved,
                "last_asked":       g.last_asked_at.isoformat() if g.last_asked_at else None,
            }
            for g in gaps
        ],
    }


@router.put("/gaps/{gap_id}/resolve")
def resolve_knowledge_gap(
    gap_id: int,
    payload: ResolveGapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a knowledge gap as resolved (after adding the missing knowledge)."""
    from app.domains.orchestration.models import KnowledgeGap
    gap = db.query(KnowledgeGap).filter(KnowledgeGap.id == gap_id).first()
    if not gap:
        raise HTTPException(status_code=404, detail="Knowledge gap not found")
    gap.is_resolved = True
    gap.resolved_by = current_user.id
    gap.resolved_at = datetime.utcnow()
    if payload.notes:
        gap.suggested_action = payload.notes
    db.commit()
    return {"message": "تم تعيين الثغرة المعرفية كمحلولة", "gap_id": gap_id}


@router.get("/routing-logs")
def list_routing_logs(
    skip: int = 0,
    limit: int = 50,
    domain: str | None = Query(None),
    confidence: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Full audit log of every routing decision made by the orchestrator."""
    from app.domains.orchestration.models import AgentRoutingLog
    q = db.query(AgentRoutingLog)
    if domain:
        q = q.filter(AgentRoutingLog.primary_domain == domain)
    if confidence:
        q = q.filter(AgentRoutingLog.retrieval_confidence == confidence.upper())
    logs = q.order_by(AgentRoutingLog.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": q.count(),
        "logs": [
            {
                "id":                  lg.id,
                "query":               lg.query,
                "primary_domain":      lg.primary_domain,
                "secondary_domains":   lg.secondary_domains,
                "routed_agent_id":     lg.routed_agent_id,
                "routing_confidence":  lg.routing_confidence,
                "retrieval_confidence": lg.retrieval_confidence,
                "results_count":       lg.results_count,
                "created_at":          lg.created_at.isoformat(),
            }
            for lg in logs
        ],
    }


@router.get("/stats")
def orchestration_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Platform-level orchestration analytics."""
    from app.domains.orchestration.models import AgentRoutingLog, KnowledgeGap, AgentHandoff
    from sqlalchemy import func

    total_queries = db.query(AgentRoutingLog).count()
    high_conf = db.query(AgentRoutingLog).filter(
        AgentRoutingLog.retrieval_confidence == "HIGH"
    ).count()
    medium_conf = db.query(AgentRoutingLog).filter(
        AgentRoutingLog.retrieval_confidence == "MEDIUM"
    ).count()
    low_conf = db.query(AgentRoutingLog).filter(
        AgentRoutingLog.retrieval_confidence.in_(["LOW", None])
    ).count()

    domain_breakdown = {}
    rows = (
        db.query(AgentRoutingLog.primary_domain, func.count(AgentRoutingLog.id))
        .group_by(AgentRoutingLog.primary_domain)
        .all()
    )
    for domain, count in rows:
        domain_breakdown[domain or "unknown"] = count

    total_gaps = db.query(KnowledgeGap).count()
    unresolved_gaps = db.query(KnowledgeGap).filter(KnowledgeGap.is_resolved == False).count()
    top_gaps = (
        db.query(KnowledgeGap)
        .filter(KnowledgeGap.is_resolved == False)
        .order_by(KnowledgeGap.occurrence_count.desc())
        .limit(5)
        .all()
    )
    total_handoffs = db.query(AgentHandoff).count()

    return {
        "queries": {
            "total":          total_queries,
            "high_confidence":   high_conf,
            "medium_confidence": medium_conf,
            "low_confidence":    low_conf,
            "success_rate":   round(
                (high_conf + medium_conf) / total_queries, 3
            ) if total_queries > 0 else 0.0,
        },
        "domain_breakdown": domain_breakdown,
        "knowledge_gaps": {
            "total":     total_gaps,
            "unresolved": unresolved_gaps,
            "top_unresolved": [
                {
                    "id":          g.id,
                    "query":       g.query,
                    "domain":      g.attempted_domain,
                    "occurrences": g.occurrence_count,
                    "action":      g.suggested_action,
                }
                for g in top_gaps
            ],
        },
        "agent_handoffs": {"total": total_handoffs},
    }
