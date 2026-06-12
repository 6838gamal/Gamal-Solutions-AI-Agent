from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class CustomerStatus(str, enum.Enum):
    LEAD = "lead"
    PROSPECT = "prospect"
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHURNED = "churned"


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), index=True)
    phone = Column(String(50))
    company = Column(String(255))
    status = Column(Enum(CustomerStatus, native_enum=False), default=CustomerStatus.LEAD)
    score = Column(Float, default=0.0)
    purchase_probability = Column(Float, default=0.0)
    lifetime_value = Column(Float, default=0.0)
    interests = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    address = Column(String(500))
    country = Column(String(100))
    notes = Column(Text)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    conversations = relationship("Conversation", back_populates="customer")


class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    title = Column(String(255), nullable=False)
    value = Column(Float, default=0.0)
    stage = Column(String(100), default="discovery")
    probability = Column(Float, default=0.0)
    close_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
