from datetime import datetime
from pydantic import BaseModel
from app.domains.knowledge.models import DocumentType, KnowledgeStatus


class CategoryBase(BaseModel):
    name: str
    name_ar: str | None = None
    description: str | None = None
    parent_id: int | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    title: str
    title_ar: str | None = None
    content: str | None = None
    summary: str | None = None
    doc_type: DocumentType = DocumentType.MANUAL
    source: str | None = None
    version: str = "1.0"
    confidence_score: float = 1.0
    tags: list = []
    category_id: int | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    summary: str | None = None
    status: KnowledgeStatus | None = None
    tags: list | None = None
    category_id: int | None = None


class DocumentOut(DocumentBase):
    id: int
    status: KnowledgeStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
