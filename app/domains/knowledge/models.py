from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DocumentType(str, enum.Enum):
    PDF       = "pdf"
    WORD      = "word"
    EXCEL     = "excel"
    CSV       = "csv"
    TEXT      = "text"
    JSON      = "json"
    URL       = "url"
    MANUAL    = "manual"
    POLICY    = "policy"
    PROCEDURE = "procedure"
    CONTRACT  = "contract"
    FAQ       = "faq"
    OTHER     = "other"


class KnowledgeStatus(str, enum.Enum):
    PROCESSING = "processing"
    ACTIVE     = "active"
    ARCHIVED   = "archived"
    ERROR      = "error"


class KnowledgeDomain(str, enum.Enum):
    """Which functional domain owns / primarily uses this document."""
    CUSTOMER_SUPPORT = "customer_support"
    SALES            = "sales"
    MARKET_INTEL     = "market_intel"
    HR               = "hr"
    FINANCE          = "finance"
    OPERATIONS       = "operations"
    PRODUCT          = "product"
    GENERAL          = "general"


class KnowledgeVisibility(str, enum.Enum):
    GLOBAL          = "global"           # all agents can access
    DOMAIN_SPECIFIC = "domain_specific"  # only agents in allowed_agent_types
    PRIVATE         = "private"          # internal only, not exposed via RAG


class KnowledgeCategory(Base):
    __tablename__ = "knowledge_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("knowledge_categories.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    documents = relationship("KnowledgeDocument", back_populates="category")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    title_ar = Column(String(500))
    content = Column(Text)
    summary = Column(Text)
    doc_type = Column(Enum(DocumentType, native_enum=False), default=DocumentType.MANUAL)
    status = Column(Enum(KnowledgeStatus, native_enum=False), default=KnowledgeStatus.ACTIVE)
    source = Column(String(500))
    version = Column(String(50), default="1.0")
    confidence_score = Column(Float, default=1.0)
    tags = Column(JSON, default=list)
    metadata_extra = Column(JSON, default=dict)
    file_path = Column(String(500))
    file_name = Column(String(255))
    file_size = Column(Integer, default=0)
    is_trained = Column(Boolean, default=False)
    trained_at = Column(DateTime, nullable=True)
    # Domain architecture fields
    domain = Column(String(50), default="general")           # KnowledgeDomain value
    visibility = Column(String(30), default="global")        # KnowledgeVisibility value
    allowed_agent_types = Column(JSON, default=list)         # [] = all agents
    importance_score = Column(Float, default=1.0)            # document-level importance
    # Retrieval analytics
    retrieval_count = Column(Integer, default=0)
    last_retrieved_at = Column(DateTime, nullable=True)
    category_id = Column(Integer, ForeignKey("knowledge_categories.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category = relationship("KnowledgeCategory", back_populates="documents")
    chunks = relationship(
        "KnowledgeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )


class KnowledgeChunk(Base):
    """
    Per-chunk storage — enables BM25 chunk-level retrieval and question matching.
    Each KnowledgeDocument has N chunks; each chunk stores its text, extracted
    keywords, and generated questions (what a user might ask that this chunk answers).
    """
    __tablename__ = "knowledge_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    keywords = Column(JSON, default=list)       # [{term, count, score}]
    questions = Column(JSON, default=list)      # ["ما هو X؟", "كيف أفعل Y؟", ...]
    section_heading = Column(String(500))
    char_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    importance_score = Column(Float, default=1.0)
    retrieval_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    document = relationship("KnowledgeDocument", back_populates="chunks")


class KnowledgeFeedback(Base):
    """
    Feedback loop — tracks whether retrieved chunks were helpful.
    Used to boost importance_score of consistently helpful chunks over time.
    """
    __tablename__ = "knowledge_feedback"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    doc_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=True)
    chunk_id = Column(Integer, ForeignKey("knowledge_chunks.id"), nullable=True)
    was_helpful = Column(Boolean, nullable=True)
    feedback_text = Column(Text)
    confidence_shown = Column(String(10))       # HIGH / MEDIUM / LOW shown to user
    created_at = Column(DateTime, default=datetime.utcnow)
