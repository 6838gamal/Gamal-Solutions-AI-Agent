from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.customers import models, schemas
from app.domains.auth.models import User

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/", response_model=list[schemas.CustomerOut])
def list_customers(
    skip: int = 0,
    limit: int = 50,
    search: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(models.Customer)
    if search:
        q = q.filter(
            models.Customer.name.ilike(f"%{search}%") |
            models.Customer.email.ilike(f"%{search}%") |
            models.Customer.company.ilike(f"%{search}%")
        )
    if status:
        q = q.filter(models.Customer.status == status)
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.CustomerOut)
def create_customer(data: schemas.CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = models.Customer(**data.model_dump(), created_by=current_user.id)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(customer_id: int, data: schemas.CustomerUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(c)
    db.commit()
    return {"message": "Customer deleted"}


@router.get("/{customer_id}/opportunities", response_model=list[schemas.OpportunityOut])
def list_opportunities(customer_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.Opportunity).filter(models.Opportunity.customer_id == customer_id).all()


@router.post("/{customer_id}/opportunities", response_model=schemas.OpportunityOut)
def create_opportunity(customer_id: int, data: schemas.OpportunityCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    opp = models.Opportunity(**data.model_dump())
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return opp
