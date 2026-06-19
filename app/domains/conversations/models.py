from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class Channel(str, enum.Enum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    INTERNAL = "internal"


class ConversationStatus(str, enum.Enum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    AGENT = "agent"
    SYSTEM = "system"


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    channel = Column(Enum(Channel, native_enum=False), default=Channel.WEB)
    status = Column(Enum(ConversationStatus, native_enum=False), default=ConversationStatus.OPEN)
    subject = Column(String(500))
    assigned_agent_id = Column(Integer, ForeignKey("agents.id"))
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    tags = Column(JSON, default=list)
    priority = Column(String(20), default="normal")
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(Enum(MessageRole, native_enum=False), nullable=False)
    content = Column(Text, nullable=False)
    metadata_extra = Column(JSON, default=dict)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="messages")
