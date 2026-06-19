from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    CSV = "csv"
    TEXT = "text"
    URL = "url"
    MANUAL = "manual"
    POLICY = "policy"
    PROCEDURE = "procedure"
    CONTRACT = "contract"
    FAQ = "faq"
    OTHER = "other"


class KnowledgeStatus(str, enum.Enum):
    PROCESSING = "processing"
    ACTIVE = "active"
    ARCHIVED = "archived"
    ERROR = "error"


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
    category_id = Column(Integer, ForeignKey("knowledge_categories.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category = relationship("KnowledgeCategory", back_populates="documents")
