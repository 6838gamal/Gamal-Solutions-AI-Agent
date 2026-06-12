from datetime import datetime
from pydantic import BaseModel
from app.domains.agents.models import AgentType, AgentStatus


class AgentBase(BaseModel):
    name: str
    name_ar: str | None = None
    description: str | None = None
    agent_type: AgentType
    system_prompt: str | None = None
    capabilities: list = []
    permissions: list = []
    config: dict = {}


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    description: str | None = None
    status: AgentStatus | None = None
    system_prompt: str | None = None
    capabilities: list | None = None
    config: dict | None = None


class AgentOut(AgentBase):
    id: int
    status: AgentStatus
    performance_score: float
    total_tasks: int
    successful_tasks: int
    created_at: datetime

    class Config:
        from_attributes = True


class DecisionOut(BaseModel):
    id: int
    agent_id: int
    task_type: str | None
    decision: str | None
    confidence: float
    requires_approval: bool
    executed: bool
    created_at: datetime

    class Config:
        from_attributes = True
