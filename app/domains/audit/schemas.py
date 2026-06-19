from datetime import datetime
from pydantic import BaseModel
from app.domains.audit.models import AuditAction


class AuditLogCreate(BaseModel):
    user_id: int | None = None
    action: AuditAction
    resource: str | None = None
    resource_id: str | None = None
    description: str | None = None
    old_values: dict | None = None
    new_values: dict | None = None
    ip_address: str | None = None
    status: str = "success"


class AuditLogOut(AuditLogCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
