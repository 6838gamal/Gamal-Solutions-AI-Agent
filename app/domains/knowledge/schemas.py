from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.domains.knowledge.models import DocumentType, KnowledgeStatus


class CategoryBase(BaseModel):
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    description: Optional[str] = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    title: str
    title_ar: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    doc_type: DocumentType = DocumentType.MANUAL
    source: Optional[str] = None
    version: str = "1.0"
    confidence_score: float = 1.0
    tags: list = []
    category_id: Optional[int] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    title_ar: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[KnowledgeStatus] = None
    doc_type: Optional[DocumentType] = None
    tags: Optional[list] = None
    category_id: Optional[int] = None
    version: Optional[str] = None


class DocumentOut(DocumentBase):
    id: int
    status: KnowledgeStatus
    file_name: Optional[str] = None
    file_size: Optional[int] = 0
    is_trained: bool = False
    trained_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
