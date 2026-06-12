from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.security import verify_password, get_password_hash, create_access_token
from app.domains.auth import models, schemas
from app.core.config import settings


def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == username)
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    existing = db.query(models.User).filter(
        (models.User.email == user_in.email) | (models.User.username == user_in.username)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    user = models.User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        department=user_in.department,
        phone=user_in.phone,
        language=user_in.language,
        is_superuser=user_in.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_users(db: Session, skip: int = 0, limit: int = 50):
    return db.query(models.User).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: int, data: schemas.UserUpdate) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: models.User, data: schemas.PasswordChange):
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    user.hashed_password = get_password_hash(data.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()


def ensure_superuser(db: Session):
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        create_user(db, schemas.UserCreate(
            email="admin@gamal-solutions.com",
            username="admin",
            full_name="System Administrator",
            password="Admin@2024!",
            is_superuser=True,
        ))
