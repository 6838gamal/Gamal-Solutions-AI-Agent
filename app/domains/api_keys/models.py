from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, JSON, String, Boolean, Text
from app.core.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False)
    key_hash    = Column(String(128), unique=True, nullable=False, index=True)
    key_prefix  = Column(String(12), nullable=False)
    permissions = Column(JSON, default=list)
    is_active   = Column(Boolean, default=True)
    description = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)
    last_used_at= Column(DateTime, nullable=True)
    expires_at  = Column(DateTime, nullable=True)
