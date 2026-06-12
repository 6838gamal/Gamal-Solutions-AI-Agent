from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.conversations import models, schemas
from app.domains.auth.models import User

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/", response_model=list[schemas.ConversationOut])
def list_conversations(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.Conversation).order_by(models.Conversation.updated_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.ConversationOut)
def create_conversation(data: schemas.ConversationCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    conv = models.Conversation(**data.model_dump())
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/{conv_id}", response_model=schemas.ConversationOut)
def get_conversation(conv_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.put("/{conv_id}", response_model=schemas.ConversationOut)
def update_conversation(conv_id: int, data: schemas.ConversationUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(conv, field, value)
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/{conv_id}/messages", response_model=list[schemas.MessageOut])
def get_messages(conv_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.Message).filter(models.Message.conversation_id == conv_id).order_by(models.Message.created_at).all()


@router.post("/{conv_id}/messages", response_model=schemas.MessageOut)
def add_message(conv_id: int, data: schemas.MessageCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg = models.Message(**data.model_dump(), conversation_id=conv_id)
    db.add(msg)
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return msg
