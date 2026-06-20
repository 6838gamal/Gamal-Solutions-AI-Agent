from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TelegramConnectionStatus(str, enum.Enum):
    DISCONNECTED = "disconnected"
    PENDING_CODE = "pending_code"
    CONNECTED = "connected"
    ERROR = "error"


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"
    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(String(50))
    api_hash = Column(String(100))
    phone = Column(String(30))
    session_string = Column(Text)
    phone_code_hash = Column(String(200))
    status = Column(String(30), default=TelegramConnectionStatus.DISCONNECTED)
    telegram_user_id = Column(String(50))
    telegram_username = Column(String(100))
    telegram_first_name = Column(String(100))
    error_message = Column(Text)
    market_analysis = Column(JSON, default=None)
    market_analysis_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = relationship("TelegramMessage", back_populates="account")
    reply_rules = relationship("TelegramReplyRule", back_populates="account")


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"))
    message_id = Column(Integer)
    chat_id = Column(String(50))
    chat_title = Column(String(255))
    chat_type = Column(String(30))
    sender_id = Column(String(50))
    sender_name = Column(String(255))
    sender_username = Column(String(100))
    content = Column(Text)
    media_type = Column(String(30))
    direction = Column(String(10), default="incoming")
    is_read = Column(Boolean, default=False)
    analysis_result = Column(JSON, default=dict)
    is_analyzed = Column(Boolean, default=False)
    reply_sent = Column(Boolean, default=False)
    replied_at = Column(DateTime)
    received_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    account = relationship("TelegramAccount", back_populates="messages")


class TelegramReplyRule(Base):
    __tablename__ = "telegram_reply_rules"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"))
    rule_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    target_type = Column(String(30), default="all")
    target_chat_id = Column(String(50))
    target_sender_username = Column(String(100))
    keywords = Column(JSON, default=list)
    reply_mode = Column(String(30), default="manual")
    agent_id = Column(Integer, ForeignKey("agents.id"))
    reply_template = Column(Text)
    reply_delay_seconds = Column(Integer, default=0)
    max_replies_per_hour = Column(Integer, default=10)
    replies_sent = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    account = relationship("TelegramAccount", back_populates="reply_rules")
    agent = relationship("Agent")
