from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.knowledge import models, schemas
from app.domains.auth.models import User

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.KnowledgeCategory).all()


@router.post("/categories", response_model=schemas.CategoryOut)
def create_category(data: schemas.CategoryCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    cat = models.KnowledgeCategory(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/documents", response_model=list[schemas.DocumentOut])
def list_documents(
    skip: int = 0,
    limit: int = 50,
    search: str | None = Query(None),
    category_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(models.KnowledgeDocument)
    if search:
        q = q.filter(
            models.KnowledgeDocument.title.ilike(f"%{search}%") |
            models.KnowledgeDocument.content.ilike(f"%{search}%")
        )
    if category_id:
        q = q.filter(models.KnowledgeDocument.category_id == category_id)
    return q.offset(skip).limit(limit).all()


@router.post("/documents", response_model=schemas.DocumentOut)
def create_document(data: schemas.DocumentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = models.KnowledgeDocument(**data.model_dump(), created_by=current_user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/documents/{doc_id}", response_model=schemas.DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/documents/{doc_id}", response_model=schemas.DocumentOut)
def update_document(doc_id: int, data: schemas.DocumentUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}
