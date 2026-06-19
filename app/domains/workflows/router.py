from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.workflows import models, schemas
from app.domains.auth.models import User

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("/", response_model=list[schemas.WorkflowOut])
def list_workflows(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.Workflow).all()


@router.post("/", response_model=schemas.WorkflowOut)
def create_workflow(data: schemas.WorkflowCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wf = models.Workflow(**data.model_dump(), created_by=current_user.id)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.put("/{wf_id}", response_model=schemas.WorkflowOut)
def update_workflow(wf_id: int, data: schemas.WorkflowUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    wf = db.query(models.Workflow).filter(models.Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(wf, field, value)
    wf.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(wf)
    return wf


@router.delete("/{wf_id}")
def delete_workflow(wf_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    wf = db.query(models.Workflow).filter(models.Workflow.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()
    return {"message": "Workflow deleted"}


task_router = APIRouter(prefix="/tasks", tags=["Tasks"])


@task_router.get("/", response_model=list[schemas.TaskOut])
def list_tasks(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(models.Task).order_by(models.Task.created_at.desc()).offset(skip).limit(limit).all()


@task_router.post("/", response_model=schemas.TaskOut)
def create_task(data: schemas.TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = models.Task(**data.model_dump(), created_by=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@task_router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, data: schemas.TaskUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task
