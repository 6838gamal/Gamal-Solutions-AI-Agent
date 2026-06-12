from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, Enum
from app.core.database import Base
import enum


class AuditAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    EXECUTE = "execute"
    ERROR = "error"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(Enum(AuditAction, native_enum=False), nullable=False)
    resource = Column(String(100))
    resource_id = Column(String(100))
    description = Column(Text)
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    status = Column(String(20), default="success")
    created_at = Column(DateTime, default=datetime.utcnow)
