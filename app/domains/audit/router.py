from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.audit import models, schemas
from app.domains.auth.models import User

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=list[schemas.AuditLogOut])
def list_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    resource: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    if user_id:
        q = q.filter(models.AuditLog.user_id == user_id)
    if action:
        q = q.filter(models.AuditLog.action == action)
    if resource:
        q = q.filter(models.AuditLog.resource == resource)
    return q.offset(skip).limit(limit).all()


@router.get("/stats")
def audit_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total = db.query(models.AuditLog).count()
    by_action = {}
    for action in models.AuditAction:
        count = db.query(models.AuditLog).filter(models.AuditLog.action == action).count()
        by_action[action.value] = count
    return {"total": total, "by_action": by_action}
