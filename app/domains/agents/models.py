from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class AgentType(str, enum.Enum):
    SALES = "sales"
    CUSTOMER_SERVICE = "customer_service"
    OPERATIONS = "operations"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRAINING = "training"
    MAINTENANCE = "maintenance"


class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    agent_type = Column(Enum(AgentType, native_enum=False), nullable=False)
    status = Column(Enum(AgentStatus, native_enum=False), default=AgentStatus.ACTIVE)
    system_prompt = Column(Text)
    capabilities = Column(JSON, default=list)
    permissions = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    performance_score = Column(Float, default=0.0)
    total_tasks = Column(Integer, default=0)
    successful_tasks = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    decisions = relationship("AgentDecision", back_populates="agent")


class AgentDecision(Base):
    __tablename__ = "agent_decisions"
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    task_type = Column(String(100))
    input_data = Column(JSON)
    decision = Column(Text)
    output_data = Column(JSON)
    confidence = Column(Float, default=0.0)
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    executed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    agent = relationship("Agent", back_populates="decisions")
