from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domains.api_keys.service import validate_key
from app.domains.api_keys.models import APIKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(
    raw_key: str = Security(api_key_header),
    db: Session = Depends(get_db),
) -> APIKey:
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مطلوب مفتاح API — أضف الترويسة: X-API-Key",
        )
    api_key = validate_key(db, raw_key)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="مفتاح API غير صالح أو منتهي الصلاحية",
        )
    return api_key


def require_permission(permission: str):
    """Dependency factory that checks a specific permission on the key."""
    def _check(api_key: APIKey = Depends(get_api_key)) -> APIKey:
        perms = api_key.permissions or []
        if "*" not in perms and permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"المفتاح لا يملك صلاحية: {permission}",
            )
        return api_key
    return _check
