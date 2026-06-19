from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, Enum, Boolean
from app.core.database import Base
import enum


class WorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowTrigger(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    API = "api"


class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    trigger = Column(Enum(WorkflowTrigger, native_enum=False), default=WorkflowTrigger.MANUAL)
    trigger_config = Column(JSON, default=dict)
    steps = Column(JSON, default=list)
    status = Column(Enum(WorkflowStatus, native_enum=False), default=WorkflowStatus.DRAFT)
    is_system = Column(Boolean, default=False)
    run_count = Column(Integer, default=0)
    last_run = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus, native_enum=False), default=TaskStatus.PENDING)
    priority = Column(String(20), default="normal")
    due_date = Column(DateTime)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    metadata_extra = Column(JSON, default=dict)
    completed_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
