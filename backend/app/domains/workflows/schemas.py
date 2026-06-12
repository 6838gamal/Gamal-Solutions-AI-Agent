from datetime import datetime
from pydantic import BaseModel
from app.domains.workflows.models import WorkflowStatus, WorkflowTrigger, TaskStatus


class WorkflowBase(BaseModel):
    name: str
    name_ar: str | None = None
    description: str | None = None
    trigger: WorkflowTrigger = WorkflowTrigger.MANUAL
    trigger_config: dict = {}
    steps: list = []


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: WorkflowStatus | None = None
    steps: list | None = None
    trigger_config: dict | None = None


class WorkflowOut(WorkflowBase):
    id: int
    status: WorkflowStatus
    run_count: int
    last_run: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    priority: str = "normal"
    due_date: datetime | None = None
    assigned_to: int | None = None
    customer_id: int | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: str | None = None
    due_date: datetime | None = None
    assigned_to: int | None = None


class TaskOut(TaskBase):
    id: int
    status: TaskStatus
    workflow_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
