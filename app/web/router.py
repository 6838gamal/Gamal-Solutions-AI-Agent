# app/web/routes.py
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import jwt
import logging
import json

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.core.templates import templates

from app.domains.auth import models as auth_models, service as auth_service
from app.domains.agents import models as agent_models
from app.domains.customers import models as customer_models
from app.domains.conversations import models as conv_models
from app.domains.knowledge import models as kb_models
from app.domains.workflows import models as wf_models
from app.domains.audit import models as audit_models
from app.domains.telegram import models as tg_models

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Web"])

COOKIE_NAME = "access_token"


# ══════════════════════════════════════════════════════════════════════════════
# Auth helpers
# ══════════════════════════════════════════════════════════════════════════════

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


def _is_https(request: Request) -> bool:
    """يتعامل بشكل صحيح مع X-Forwarded-Proto خلف Proxy/Render/Cloudflare."""
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return proto == "https"


def _safe_json(obj) -> str:
    """JSON آمن للحقن في <script> — يحمي من </script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

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
    try:
        user = auth_service.authenticate_user(db, username, password)
        if not user or not user.is_active:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "بيانات الدخول غير صحيحة"},
                status_code=200,
            )
        token = create_access_token(subject=user.id)
        response = RedirectResponse(url="/dashboard", status_code=302)
        secure = _is_https(request)
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
            secure=secure,
            path="/",
        )
        return response
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "خطأ في الخادم، يرجى المحاولة لاحقاً"},
            status_code=500,
        )


@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    secure = _is_https(request)
    response.delete_cookie(COOKIE_NAME, path="/", secure=secure, httponly=True, samesite="lax")
    return response


@router.get("/session-check")
def session_check(request: Request, db: Session = Depends(get_db)):
    """فحص جلسة خفيف لحماية زر الرجوع في المتصفح."""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return JSONResponse({"authenticated": False}, status_code=401)
    return JSONResponse({"authenticated": True})


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    stats = {
        "total_users":         db.query(auth_models.User).count(),
        "total_agents":        db.query(agent_models.Agent).count(),
        "active_agents":       db.query(agent_models.Agent).filter(
                                   agent_models.Agent.status == agent_models.AgentStatus.ACTIVE).count(),
        "total_customers":     db.query(customer_models.Customer).count(),
        "total_conversations": db.query(conv_models.Conversation).count(),
        "open_conversations":  db.query(conv_models.Conversation).filter(
                                   conv_models.Conversation.status == conv_models.ConversationStatus.OPEN).count(),
        "total_documents":     db.query(kb_models.KnowledgeDocument).count(),
        "total_workflows":     db.query(wf_models.Workflow).count(),
        "total_tasks":         db.query(wf_models.Task).count(),
        "pending_tasks":       db.query(wf_models.Task).filter(
                                   wf_models.Task.status == wf_models.TaskStatus.PENDING).count(),
    }

    customer_by_status = {
        s.value: db.query(customer_models.Customer)
                   .filter(customer_models.Customer.status == s).count()
        for s in customer_models.CustomerStatus
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "customer_by_status": customer_by_status,
        "page": "dashboard",
    })


# ══════════════════════════════════════════════════════════════════════════════
# AGENTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/agents", response_class=HTMLResponse)
def agents_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    agents = db.query(agent_models.Agent).order_by(agent_models.Agent.created_at.desc()).all()
    return templates.TemplateResponse("agents.html", {
        "request": request,
        "user": user,
        "agents": agents,
        "page": "agents",
        "AgentStatus": agent_models.AgentStatus,
        "AgentType": agent_models.AgentType,
    })


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════

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
        "request": request,
        "user": user,
        "customers": customers,
        "page": "customers",
        "search": search,
        "CustomerStatus": customer_models.CustomerStatus,
    })


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/conversations", response_class=HTMLResponse)
def conversations_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conversations = db.query(conv_models.Conversation)\
        .order_by(conv_models.Conversation.created_at.desc()).all()
    return templates.TemplateResponse("conversations.html", {
        "request": request,
        "user": user,
        "conversations": conversations,
        "page": "conversations",
        "ConversationStatus": conv_models.ConversationStatus,
    })


# ══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/knowledge", response_class=HTMLResponse)
def knowledge_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    documents = db.query(kb_models.KnowledgeDocument)\
        .order_by(kb_models.KnowledgeDocument.created_at.desc()).all()
    categories = db.query(kb_models.KnowledgeCategory).all()

    try:
        trained_docs = sum(1 for d in documents if d.is_trained)
    except Exception:
        trained_docs = 0

    return templates.TemplateResponse("knowledge.html", {
        "request": request,
        "user": user,
        "documents": documents,
        "categories": categories,
        "page": "knowledge",
        "stats": {
            "total":      len(documents),
            "trained":    trained_docs,
            "processing": sum(1 for d in documents if d.status == kb_models.KnowledgeStatus.PROCESSING),
            "active":     sum(1 for d in documents if d.status == kb_models.KnowledgeStatus.ACTIVE),
            "categories": len(categories),
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    tasks = db.query(wf_models.Task).order_by(wf_models.Task.created_at.desc()).all()
    return templates.TemplateResponse("tasks.html", {
        "request": request,
        "user": user,
        "tasks": tasks,
        "page": "tasks",
        "TaskStatus": wf_models.TaskStatus,
    })


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOWS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/workflows", response_class=HTMLResponse)
def workflows_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    workflows = db.query(wf_models.Workflow)\
        .order_by(wf_models.Workflow.created_at.desc()).all()
    return templates.TemplateResponse("workflows.html", {
        "request": request,
        "user": user,
        "workflows": workflows,
        "page": "workflows",
        "WorkflowStatus": wf_models.WorkflowStatus,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    agent_by_status = {
        s.value: db.query(agent_models.Agent)
                   .filter(agent_models.Agent.status == s).count()
        for s in agent_models.AgentStatus
    }
    customer_by_status = {
        s.value: db.query(customer_models.Customer)
                   .filter(customer_models.Customer.status == s).count()
        for s in customer_models.CustomerStatus
    }
    conv_by_status = {
        s.value: db.query(conv_models.Conversation)
                   .filter(conv_models.Conversation.status == s).count()
        for s in conv_models.ConversationStatus
    }
    task_by_status = {
        s.value: db.query(wf_models.Task)
                   .filter(wf_models.Task.status == s).count()
        for s in wf_models.TaskStatus
    }

    tg_account = db.query(tg_models.TelegramAccount).first()
    tg_market = tg_account.market_analysis if tg_account and tg_account.market_analysis else None
    tg_market_at = (
        tg_account.market_analysis_at.strftime("%Y-%m-%d %H:%M")
        if tg_account and tg_account.market_analysis_at else None
    )
    tg_total_msgs = db.query(tg_models.TelegramMessage).count() if tg_account else 0

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "user": user,
        "page": "analytics",
        "agent_by_status": agent_by_status,
        "customer_by_status": customer_by_status,
        "conv_by_status": conv_by_status,
        "task_by_status": task_by_status,
        "total_agents": db.query(agent_models.Agent).count(),
        "total_customers": db.query(customer_models.Customer).count(),
        "total_conversations": db.query(conv_models.Conversation).count(),
        "total_tasks": db.query(wf_models.Task).count(),
        "tg_market": tg_market,
        "tg_market_at": tg_market_at,
        "tg_total_msgs": tg_total_msgs,
    })


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    logs = db.query(audit_models.AuditLog)\
        .order_by(audit_models.AuditLog.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("audit.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "page": "audit",
    })


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or not user.is_superuser:
        return RedirectResponse(url="/dashboard", status_code=302)
    users = db.query(auth_models.User).order_by(auth_models.User.created_at.desc()).all()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "user": user,
        "users": users,
        "page": "users",
    })


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": user,
        "page": "settings",
        "success": None,
        "error": None,
    })


# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/telegram", response_class=HTMLResponse)
def telegram_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        account = db.query(tg_models.TelegramAccount).first()
        messages = []
        rules = []
        if account:
            messages = db.query(tg_models.TelegramMessage)\
                .filter_by(account_id=account.id)\
                .order_by(tg_models.TelegramMessage.received_at.desc())\
                .limit(200).all()
            rules = db.query(tg_models.TelegramReplyRule)\
                .filter_by(account_id=account.id).all()
    except Exception:
        account, messages, rules = None, [], []

    def msg_to_dict(m):
        return {
            "id": m.id,
            "message_id": m.message_id,
            "chat_id": m.chat_id,
            "chat_title": m.chat_title or "",
            "chat_type": m.chat_type or "",
            "sender_id": m.sender_id or "",
            "sender_name": m.sender_name or "مجهول",
            "sender_username": m.sender_username or "",
            "content": m.content or "",
            "direction": m.direction or "incoming",
            "is_read": m.is_read,
            "is_analyzed": m.is_analyzed,
            "analysis_result": m.analysis_result or {},
            "reply_sent": m.reply_sent,
            "replied_at": m.replied_at.isoformat() if m.replied_at else None,
            "received_at": m.received_at.isoformat() if m.received_at else None,
        }

    def rule_to_dict(r):
        return {
            "id": r.id,
            "rule_name": r.rule_name,
            "is_active": r.is_active,
            "target_type": r.target_type,
            "keywords": r.keywords or [],
            "reply_mode": r.reply_mode,
            "reply_template": r.reply_template or "",
            "replies_sent": r.replies_sent,
        }

    return templates.TemplateResponse("telegram.html", {
        "request": request,
        "user": user,
        "page": "telegram",
        "account": account,
        "messages": messages,
        "messages_json": _safe_json([msg_to_dict(m) for m in messages]),
        "rules_json": _safe_json([rule_to_dict(r) for r in rules]),
    })


# ══════════════════════════════════════════════════════════════════════════════
# WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/whatsapp", response_class=HTMLResponse)
def whatsapp_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    account, messages, rules = None, [], []
    try:
        from app.domains.whatsapp import models as wa_models
        account = db.query(wa_models.WhatsAppAccount).first()
        if account:
            messages = db.query(wa_models.WhatsAppMessage)\
                .filter_by(account_id=account.id)\
                .order_by(wa_models.WhatsAppMessage.received_at.desc())\
                .limit(200).all()
            rules = db.query(wa_models.WhatsAppReplyRule)\
                .filter_by(account_id=account.id).all()
    except Exception as e:
        logger.exception("Failed to load WhatsApp data: %s", e)

    def msg_to_dict(m):
        return {
            "id": m.id,
            "message_id": getattr(m, "message_id", ""),
            "chat_id": getattr(m, "chat_id", ""),
            "chat_title": getattr(m, "chat_title", "") or "",
            "sender_name": getattr(m, "sender_name", "") or "مجهول",
            "sender_phone": getattr(m, "sender_phone", "") or "",
            "content": getattr(m, "content", "") or "",
            "direction": getattr(m, "direction", "incoming"),
            "is_read": getattr(m, "is_read", False),
            "is_analyzed": getattr(m, "is_analyzed", False),
            "analysis_result": getattr(m, "analysis_result", {}) or {},
            "reply_sent": getattr(m, "reply_sent", False),
            "received_at": m.received_at.isoformat() if getattr(m, "received_at", None) else None,
        }

    def rule_to_dict(r):
        return {
            "id": r.id,
            "rule_name": getattr(r, "rule_name", ""),
            "is_active": getattr(r, "is_active", True),
            "keywords": getattr(r, "keywords", []) or [],
            "reply_mode": getattr(r, "reply_mode", "auto"),
            "reply_template": getattr(r, "reply_template", "") or "",
            "replies_sent": getattr(r, "replies_sent", 0),
        }

    return templates.TemplateResponse("whatsapp.html", {
        "request": request,
        "user": user,
        "page": "whatsapp",
        "account": account,
        "messages": messages,
        "messages_json": _safe_json([msg_to_dict(m) for m in messages]),
        "rules_json": _safe_json([rule_to_dict(r) for r in rules]),
    })


# ══════════════════════════════════════════════════════════════════════════════
# FACEBOOK
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/facebook", response_class=HTMLResponse)
def facebook_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    account, messages, rules = None, [], []
    try:
        from app.domains.facebook import models as fb_models
        account = db.query(fb_models.FacebookAccount).first()
        if account:
            messages = db.query(fb_models.FacebookMessage)\
                .filter_by(account_id=account.id)\
                .order_by(fb_models.FacebookMessage.received_at.desc())\
                .limit(200).all()
            rules = db.query(fb_models.FacebookReplyRule)\
                .filter_by(account_id=account.id).all()
    except Exception as e:
        logger.exception("Failed to load Facebook data: %s", e)

    def msg_to_dict(m):
        return {
            "id": m.id,
            "message_id": getattr(m, "message_id", ""),
            "page_id": getattr(m, "page_id", ""),
            "sender_name": getattr(m, "sender_name", "") or "مجهول",
            "sender_id": getattr(m, "sender_id", "") or "",
            "content": getattr(m, "content", "") or "",
            "direction": getattr(m, "direction", "incoming"),
            "is_read": getattr(m, "is_read", False),
            "is_analyzed": getattr(m, "is_analyzed", False),
            "analysis_result": getattr(m, "analysis_result", {}) or {},
            "reply_sent": getattr(m, "reply_sent", False),
            "received_at": m.received_at.isoformat() if getattr(m, "received_at", None) else None,
        }

    def rule_to_dict(r):
        return {
            "id": r.id,
            "rule_name": getattr(r, "rule_name", ""),
            "is_active": getattr(r, "is_active", True),
            "keywords": getattr(r, "keywords", []) or [],
            "reply_mode": getattr(r, "reply_mode", "auto"),
            "reply_template": getattr(r, "reply_template", "") or "",
            "replies_sent": getattr(r, "replies_sent", 0),
        }

    return templates.TemplateResponse("facebook.html", {
        "request": request,
        "user": user,
        "page": "facebook",
        "account": account,
        "messages": messages,
        "messages_json": _safe_json([msg_to_dict(m) for m in messages]),
        "rules_json": _safe_json([rule_to_dict(r) for r in rules]),
    })


# ══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/instagram", response_class=HTMLResponse)
def instagram_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    account, messages, rules = None, [], []
    try:
        from app.domains.instagram import models as ig_models
        account = db.query(ig_models.InstagramAccount).first()
        if account:
            messages = db.query(ig_models.InstagramMessage)\
                .filter_by(account_id=account.id)\
                .order_by(ig_models.InstagramMessage.received_at.desc())\
                .limit(200).all()
            rules = db.query(ig_models.InstagramReplyRule)\
                .filter_by(account_id=account.id).all()
    except Exception as e:
        logger.exception("Failed to load Instagram data: %s", e)

    def msg_to_dict(m):
        return {
            "id": m.id,
            "message_id": getattr(m, "message_id", ""),
            "ig_user_id": getattr(m, "ig_user_id", ""),
            "username": getattr(m, "username", "") or "مجهول",
            "content": getattr(m, "content", "") or "",
            "media_type": getattr(m, "media_type", "") or "",
            "direction": getattr(m, "direction", "incoming"),
            "is_read": getattr(m, "is_read", False),
            "is_analyzed": getattr(m, "is_analyzed", False),
            "analysis_result": getattr(m, "analysis_result", {}) or {},
            "reply_sent": getattr(m, "reply_sent", False),
            "received_at": m.received_at.isoformat() if getattr(m, "received_at", None) else None,
        }

    def rule_to_dict(r):
        return {
            "id": r.id,
            "rule_name": getattr(r, "rule_name", ""),
            "is_active": getattr(r, "is_active", True),
            "keywords": getattr(r, "keywords", []) or [],
            "reply_mode": getattr(r, "reply_mode", "auto"),
            "reply_template": getattr(r, "reply_template", "") or "",
            "replies_sent": getattr(r, "replies_sent", 0),
        }

    return templates.TemplateResponse("instagram.html", {
        "request": request,
        "user": user,
        "page": "instagram",
        "account": account,
        "messages": messages,
        "messages_json": _safe_json([msg_to_dict(m) for m in messages]),
        "rules_json": _safe_json([rule_to_dict(r) for r in rules]),
    })


# ══════════════════════════════════════════════════════════════════════════════
# REDDIT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/reddit", response_class=HTMLResponse)
def reddit_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    account, posts, comments, rules = None, [], [], []
    try:
        from app.domains.reddit import models as rd_models
        account = db.query(rd_models.RedditAccount).first()
        if account:
            posts = db.query(rd_models.RedditPost)\
                .filter_by(account_id=account.id)\
                .order_by(rd_models.RedditPost.created_at.desc())\
                .limit(200).all()
            comments = db.query(rd_models.RedditComment)\
                .filter_by(account_id=account.id)\
                .order_by(rd_models.RedditComment.created_at.desc())\
                .limit(200).all()
            rules = db.query(rd_models.RedditReplyRule)\
                .filter_by(account_id=account.id).all()
    except Exception as e:
        logger.exception("Failed to load Reddit data: %s", e)

    def post_to_dict(p):
        return {
            "id": p.id,
            "post_id": getattr(p, "post_id", ""),
            "subreddit": getattr(p, "subreddit", "") or "",
            "title": getattr(p, "title", "") or "",
            "body": getattr(p, "body", "") or "",
            "author": getattr(p, "author", "") or "مجهول",
            "score": getattr(p, "score", 0),
            "url": getattr(p, "url", "") or "",
            "is_analyzed": getattr(p, "is_analyzed", False),
            "analysis_result": getattr(p, "analysis_result", {}) or {},
            "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
        }

    def rule_to_dict(r):
        return {
            "id": r.id,
            "rule_name": getattr(r, "rule_name", ""),
            "is_active": getattr(r, "is_active", True),
            "subreddits": getattr(r, "subreddits", []) or [],
            "keywords": getattr(r, "keywords", []) or [],
            "reply_mode": getattr(r, "reply_mode", "auto"),
            "reply_template": getattr(r, "reply_template", "") or "",
            "replies_sent": getattr(r, "replies_sent", 0),
        }

    return templates.TemplateResponse("reddit.html", {
        "request": request,
        "user": user,
        "page": "reddit",
        "account": account,
        "posts": posts,
        "comments": comments,
        "posts_json": _safe_json([post_to_dict(p) for p in posts]),
        "rules_json": _safe_json([rule_to_dict(r) for r in rules]),
    })


# ══════════════════════════════════════════════════════════════════════════════
# TIKTOK
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/tiktok", response_class=HTMLResponse)
def tiktok_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    account, videos, comments, rules = None, [], [], []
    try:
        from app.domains.tiktok import models as tt_models
        account = db.query(tt_models.TikTokAccount).first()
        if account:
            videos = db.query(tt_models.TikTokVideo)\
                .filter_by(account_id=account.id)\
                .order_by(tt_models.TikTokVideo.created_at.desc())\
                .limit(200).all()
            comments = db.query(tt_models.TikTokComment)\
                .filter_by(account_id=account.id)\
                .order_by(tt_models.TikTokComment.created_at.desc())\
                .limit(200).all()
            rules = db.query(tt_models.TikTokReplyRule)\
                .filter_by(account_id=account.id).all()
    except Exception as e:
        logger.exception("Failed to load TikTok data: %s", e)

    def video_to_dict(v):
        return {
            "id": v.id,
            "video_id": getattr(v, "video_id", ""),
            "title": getattr(v, "title", "") or "",
            "description": getattr(v, "description", "") or "",
            "author": getattr(v, "author", "") or "مجهول",
            "views": getattr(v, "views", 0),
            "likes": getattr(v, "likes", 0),
            "comments_count": getattr(v, "comments_count", 0),
            "shares": getattr(v, "shares", 0),
            "url": getattr(v, "url", "") or "",
            "is_analyzed": getattr(v, "is_analyzed", False),
            "analysis_result": getattr(v, "analysis_result", {}) or {},
            "created_at": v.created_at.isoformat() if getattr(v, "created_at", None) else None,
        }

    def rule_to_dict(r):
        return {
            "id": r.id,
            "rule_name": getattr(r, "rule_name", ""),
            "is_active": getattr(r, "is_active", True),
            "keywords": getattr(r, "keywords", []) or [],
            "reply_mode": getattr(r, "reply_mode", "auto"),
            "reply_template": getattr(r, "reply_template", "") or "",
            "replies_sent": getattr(r, "replies_sent", 0),
        }

    return templates.TemplateResponse("tiktok.html", {
        "request": request,
        "user": user,
        "page": "tiktok",
        "account": account,
        "videos": videos,
        "comments": comments,
        "videos_json": _safe_json([video_to_dict(v) for v in videos]),
        "rules_json": _safe_json([rule_to_dict(r) for r in rules]),
    })


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE TRENDS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/google-trends", response_class=HTMLResponse)
def google_trends_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    trends = []
    interest_over_time = []
    related_queries = []
    try:
        from app.domains.google_trends import models as gt_models
        trends = db.query(gt_models.TrendKeyword)\
            .order_by(gt_models.TrendKeyword.created_at.desc())\
            .limit(200).all()
    except Exception as e:
        logger.exception("Failed to load Google Trends data: %s", e)

    def trend_to_dict(t):
        return {
            "id": t.id,
            "keyword": getattr(t, "keyword", ""),
            "geo": getattr(t, "geo", "") or "",
            "category": getattr(t, "category", "") or "",
            "interest_score": getattr(t, "interest_score", 0),
            "trend_direction": getattr(t, "trend_direction", "") or "",
            "is_analyzed": getattr(t, "is_analyzed", False),
            "analysis_result": getattr(t, "analysis_result", {}) or {},
            "created_at": t.created_at.isoformat() if getattr(t, "created_at", None) else None,
        }

    return templates.TemplateResponse("google_trends.html", {
        "request": request,
        "user": user,
        "page": "google-trends",
        "trends": trends,
        "trends_json": _safe_json([trend_to_dict(t) for t in trends]),
        "interest_over_time_json": _safe_json(interest_over_time),
        "related_queries_json": _safe_json(related_queries),
    })


# ══════════════════════════════════════════════════════════════════════════════
# API SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/api-settings", response_class=HTMLResponse)
def api_settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    from app.domains.api_keys.service import list_keys
    keys = list_keys(db)
    keys_data = [
        {
            "id":           k.id,
            "name":         k.name,
            "key_prefix":   k.key_prefix,
            "permissions":  k.permissions or [],
            "is_active":    k.is_active,
            "description":  k.description or "",
            "created_at":   k.created_at.strftime("%Y-%m-%d %H:%M") if k.created_at else "—",
            "last_used_at": k.last_used_at.strftime("%Y-%m-%d %H:%M") if k.last_used_at else "—",
        }
        for k in keys
    ]
    return templates.TemplateResponse("api_settings.html", {
        "request": request,
        "user": user,
        "page": "api-settings",
        "keys": keys_data,
        "keys_json": _safe_json(keys_data),
    })
