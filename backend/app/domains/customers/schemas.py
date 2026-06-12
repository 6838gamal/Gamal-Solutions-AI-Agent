from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.domains.customers.models import CustomerStatus


class CustomerBase(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    status: CustomerStatus = CustomerStatus.LEAD
    interests: list = []
    tags: list = []
    address: str | None = None
    country: str | None = None
    notes: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    status: CustomerStatus | None = None
    score: float | None = None
    purchase_probability: float | None = None
    interests: list | None = None
    notes: str | None = None
    assigned_to: int | None = None


class CustomerOut(CustomerBase):
    id: int
    score: float
    purchase_probability: float
    lifetime_value: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OpportunityBase(BaseModel):
    customer_id: int
    title: str
    value: float = 0.0
    stage: str = "discovery"
    probability: float = 0.0
    notes: str | None = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityOut(OpportunityBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
