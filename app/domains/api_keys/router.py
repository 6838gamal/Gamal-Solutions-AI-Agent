"""إدارة مفاتيح API الداخلية — مصادقة بـ JWT (للمشرفين فقط)."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_superuser
from app.domains.auth.models import User
from app.domains.api_keys import service as key_service
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class KeyCreate(BaseModel):
    name:        str
    permissions: List[str] = ["messages:read", "customers:read", "conversations:read", "analytics:read"]
    description: str = ""


@router.get("/")
def list_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    keys = key_service.list_keys(db)
    return [
        {
            "id":           k.id,
            "name":         k.name,
            "key_prefix":   k.key_prefix,
            "permissions":  k.permissions,
            "is_active":    k.is_active,
            "description":  k.description,
            "created_at":   k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]


@router.post("/generate")
def generate_key(
    body: KeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    result = key_service.generate_key(db, body.name, body.permissions, body.description)
    return JSONResponse({
        "success":    True,
        "message":    "تم توليد المفتاح — احتفظ به الآن، لن يُعرض مجدداً",
        "key":        result["key"],
        "prefix":     result["prefix"],
        "id":         result["id"],
    })


@router.post("/{key_id}/revoke")
def revoke_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    ok = key_service.revoke_key(db, key_id)
    return JSONResponse({"success": ok, "message": "تم تعطيل المفتاح" if ok else "المفتاح غير موجود"})


@router.delete("/{key_id}")
def delete_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    ok = key_service.delete_key(db, key_id)
    return JSONResponse({"success": ok, "message": "تم حذف المفتاح" if ok else "المفتاح غير موجود"})
