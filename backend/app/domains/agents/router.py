from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.agents import models, schemas
from app.domains.auth.models import User

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/", response_model=list[schemas.AgentOut])
def list_agents(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.Agent).all()


@router.post("/", response_model=schemas.AgentOut)
def create_agent(data: schemas.AgentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    agent = models.Agent(**data.model_dump(), created_by=current_user.id)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=schemas.AgentOut)
def get_agent(agent_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=schemas.AgentOut)
def update_agent(agent_id: int, data: schemas.AgentUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.delete(agent)
    db.commit()
    return {"message": "Agent deleted"}


@router.get("/{agent_id}/decisions", response_model=list[schemas.DecisionOut])
def get_agent_decisions(agent_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.AgentDecision).filter(models.AgentDecision.agent_id == agent_id).all()
