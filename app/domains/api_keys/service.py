import secrets
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from app.domains.api_keys.models import APIKey


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_key(db: Session, name: str, permissions: list, description: str = "") -> dict:
    """Generate a new API key. Returns the raw key ONCE — store it safely."""
    raw = "jml_" + secrets.token_urlsafe(32)
    prefix = raw[:12]
    key_hash = _hash_key(raw)
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        key_prefix=prefix,
        permissions=permissions,
        description=description,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {"id": api_key.id, "key": raw, "prefix": prefix, "name": name}


def validate_key(db: Session, raw: str) -> APIKey | None:
    """Validate an API key and update last_used_at."""
    key_hash = _hash_key(raw)
    api_key = db.query(APIKey).filter_by(key_hash=key_hash, is_active=True).first()
    if api_key:
        api_key.last_used_at = datetime.utcnow()
        db.commit()
    return api_key


def list_keys(db: Session) -> list:
    return db.query(APIKey).order_by(APIKey.created_at.desc()).all()


def revoke_key(db: Session, key_id: int) -> bool:
    api_key = db.query(APIKey).filter_by(id=key_id).first()
    if not api_key:
        return False
    api_key.is_active = False
    db.commit()
    return True


def delete_key(db: Session, key_id: int) -> bool:
    api_key = db.query(APIKey).filter_by(id=key_id).first()
    if not api_key:
        return False
    db.delete(api_key)
    db.commit()
    return True
