from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.domains.auth import models as auth_models, service as auth_service
from app.domains.agents import models as agent_models
from app.domains.customers import models as customer_models
from app.domains.conversations import models as conv_models
from app.domains.knowledge import models as kb_models
from app.domains.workflows import models as wf_models
from app.domains.audit import models as audit_models

import os

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

router = APIRouter(tags=["Web"])

COOKIE_NAME = "access_token"


def get_current_user_from_cookie(request: Request, db: Session) -> Optional[auth_models.User]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user = db.query(auth_models.User).filter(auth_models.User.id == int(user_id)).first()
        return user if user and user.is_active else None
    except Exception:
        return None


def require_user(request: Request, db: Session) -> Optional[auth_models.User]:
    user = get_current_user_from_cookie(request, db)
    if not user:
        return None
    return user


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = auth_service.authenticate_user(db, username, password)
    if not user or not user.is_active:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "بيانات الدخول غير صحيحة"}
        )
    token = create_access_token(subject=user.id)
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    stats = {
        "total_users": db.query(auth_models.User).count(),
        "total_agents": db.query(agent_models.Agent).count(),
        "active_agents": db.query(agent_models.Agent).filter(agent_models.Agent.status == agent_models.AgentStatus.ACTIVE).count(),
        "total_customers": db.query(customer_models.Customer).count(),
        "total_conversations": db.query(conv_models.Conversation).count(),
        "open_conversations": db.query(conv_models.Conversation).filter(conv_models.Conversation.status == conv_models.ConversationStatus.OPEN).count(),
        "total_documents": db.query(kb_models.KnowledgeDocument).count(),
        "total_workflows": db.query(wf_models.Workflow).count(),
        "total_tasks": db.query(wf_models.Task).count(),
        "pending_tasks": db.query(wf_models.Task).filter(wf_models.Task.status == wf_models.TaskStatus.PENDING).count(),
    }
    customer_by_status = {}
    for s in customer_models.CustomerStatus:
        customer_by_status[s.value] = db.query(customer_models.Customer).filter(customer_models.Customer.status == s).count()

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "stats": stats,
        "customer_by_status": customer_by_status, "page": "dashboard"
    })


# ─── AGENTS ───────────────────────────────────────────────────────────────────

@router.get("/agents", response_class=HTMLResponse)
def agents_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    agents = db.query(agent_models.Agent).order_by(agent_models.Agent.created_at.desc()).all()
    return templates.TemplateResponse("agents.html", {
        "request": request, "user": user, "agents": agents, "page": "agents",
        "AgentStatus": agent_models.AgentStatus, "AgentType": agent_models.AgentType
    })


# ─── CUSTOMERS ────────────────────────────────────────────────────────────────

@router.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, db: Session = Depends(get_db), search: str = ""):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    q = db.query(customer_models.Customer)
    if search:
        q = q.filter(customer_models.Customer.name.ilike(f"%{search}%"))
    customers = q.order_by(customer_models.Customer.created_at.desc()).all()
    return templates.TemplateResponse("customers.html", {
        "request": request, "user": user, "customers": customers,
        "page": "customers", "search": search,
        "CustomerStatus": customer_models.CustomerStatus
    })


# ─── CONVERSATIONS ────────────────────────────────────────────────────────────

@router.get("/conversations", response_class=HTMLResponse)
def conversations_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conversations = db.query(conv_models.Conversation).order_by(conv_models.Conversation.created_at.desc()).all()
    return templates.TemplateResponse("conversations.html", {
        "request": request, "user": user, "conversations": conversations,
        "page": "conversations", "ConversationStatus": conv_models.ConversationStatus
    })


# ─── KNOWLEDGE ────────────────────────────────────────────────────────────────

@router.get("/knowledge", response_class=HTMLResponse)
def knowledge_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    documents = db.query(kb_models.KnowledgeDocument).order_by(kb_models.KnowledgeDocument.created_at.desc()).all()
    categories = db.query(kb_models.KnowledgeCategory).all()
    return templates.TemplateResponse("knowledge.html", {
        "request": request, "user": user, "documents": documents,
        "categories": categories, "page": "knowledge"
    })


# ─── TASKS ────────────────────────────────────────────────────────────────────

@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    tasks = db.query(wf_models.Task).order_by(wf_models.Task.created_at.desc()).all()
    return templates.TemplateResponse("tasks.html", {
        "request": request, "user": user, "tasks": tasks,
        "page": "tasks", "TaskStatus": wf_models.TaskStatus
    })


# ─── WORKFLOWS ────────────────────────────────────────────────────────────────

@router.get("/workflows", response_class=HTMLResponse)
def workflows_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    workflows = db.query(wf_models.Workflow).order_by(wf_models.Workflow.created_at.desc()).all()
    return templates.TemplateResponse("workflows.html", {
        "request": request, "user": user, "workflows": workflows,
        "page": "workflows", "WorkflowStatus": wf_models.WorkflowStatus
    })


# ─── ANALYTICS ────────────────────────────────────────────────────────────────

@router.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    agent_by_status = {}
    for s in agent_models.AgentStatus:
        agent_by_status[s.value] = db.query(agent_models.Agent).filter(agent_models.Agent.status == s).count()

    customer_by_status = {}
    for s in customer_models.CustomerStatus:
        customer_by_status[s.value] = db.query(customer_models.Customer).filter(customer_models.Customer.status == s).count()

    conv_by_status = {}
    for s in conv_models.ConversationStatus:
        conv_by_status[s.value] = db.query(conv_models.Conversation).filter(conv_models.Conversation.status == s).count()

    task_by_status = {}
    for s in wf_models.TaskStatus:
        task_by_status[s.value] = db.query(wf_models.Task).filter(wf_models.Task.status == s).count()

    return templates.TemplateResponse("analytics.html", {
        "request": request, "user": user, "page": "analytics",
        "agent_by_status": agent_by_status,
        "customer_by_status": customer_by_status,
        "conv_by_status": conv_by_status,
        "task_by_status": task_by_status,
        "total_agents": db.query(agent_models.Agent).count(),
        "total_customers": db.query(customer_models.Customer).count(),
        "total_conversations": db.query(conv_models.Conversation).count(),
        "total_tasks": db.query(wf_models.Task).count(),
    })


# ─── AUDIT LOGS ───────────────────────────────────────────────────────────────

@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    logs = db.query(audit_models.AuditLog).order_by(audit_models.AuditLog.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("audit.html", {
        "request": request, "user": user, "logs": logs, "page": "audit"
    })


# ─── USERS ────────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/dashboard", status_code=302)
    users = db.query(auth_models.User).order_by(auth_models.User.created_at.desc()).all()
    return templates.TemplateResponse("users.html", {
        "request": request, "user": user, "users": users, "page": "users"
    })


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("settings.html", {
        "request": request, "user": user, "page": "settings", "success": None, "error": None
    })
