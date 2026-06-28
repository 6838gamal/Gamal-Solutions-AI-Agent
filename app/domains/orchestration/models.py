"""
Orchestration Layer Models
══════════════════════════
- AgentRoutingLog   : every routing decision (query → agent + domain)
- KnowledgeGap      : queries that got LOW/no confidence (continuous learning)
- AgentHandoff      : when one agent transfers a task to another
"""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class AgentRoutingLog(Base):
    """Records every routing decision made by the Knowledge Router."""
    __tablename__ = "agent_routing_logs"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    primary_domain = Column(String(50))           # customer_support, sales, market_intel…
    secondary_domains = Column(JSON, default=list) # other domains involved
    routed_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    routing_confidence = Column(Float, default=0.0)
    domain_scores = Column(JSON, default=dict)     # {domain: score}
    matched_signals = Column(JSON, default=list)   # which keywords triggered routing
    retrieval_confidence = Column(String(10))       # HIGH / MEDIUM / LOW
    results_count = Column(Integer, default=0)
    session_id = Column(String(100))               # link to conversation
    created_at = Column(DateTime, default=datetime.utcnow)
    agent = relationship("Agent", foreign_keys=[routed_agent_id])


class KnowledgeGap(Base):
    """
    Continuous Learning — tracks queries that couldn't be answered well.
    Each gap is a signal to add/update knowledge in that domain.
    """
    __tablename__ = "knowledge_gaps"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    attempted_domain = Column(String(50))
    retrieval_confidence = Column(String(10))      # always LOW or NONE here
    top_score = Column(Float, default=0.0)         # best BM25 score achieved
    suggested_domain = Column(String(50))          # where to add the knowledge
    suggested_action = Column(Text)                # human-readable recommendation
    is_resolved = Column(Boolean, default=False)   # marked resolved after KB update
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    occurrence_count = Column(Integer, default=1)  # how many times asked
    last_asked_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentHandoff(Base):
    """
    Agent-to-Agent communication log.
    When Agent A cannot handle a query, it hands off to Agent B.
    """
    __tablename__ = "agent_handoffs"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    from_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    to_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    reason = Column(Text)                          # why handoff occurred
    context = Column(JSON, default=dict)           # shared context passed along
    status = Column(String(30), default="pending") # pending, accepted, completed
    result = Column(Text)                          # final outcome
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    from_agent = relationship("Agent", foreign_keys=[from_agent_id])
    to_agent = relationship("Agent", foreign_keys=[to_agent_id])
