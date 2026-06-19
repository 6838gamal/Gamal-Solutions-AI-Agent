from datetime import datetime
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None
    department: str | None = None
    phone: str | None = None
    language: str = "ar"


class UserCreate(UserBase):
    password: str
    is_superuser: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    phone: str | None = None
    language: str | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleOut(RoleBase):
    id: int
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserOut(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: datetime | None = None
    roles: list[RoleOut] = []

    class Config:
        from_attributes = True
