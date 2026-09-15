from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import jwt
import logging
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
from app.domains.telegram import models as tg_models

from app.domains.youtube.web import router as youtube_web_router


import json
import os

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

# ─── Jinja2 Globals ────────────────────────────────────────────────────────────

_TYPE_BG = {
    'pdf': 'bg-red-100', 'word': 'bg-blue-100', 'excel': 'bg-emerald-100',
    'csv': 'bg-teal-100', 'text': 'bg-slate-100', 'json': 'bg-amber-100',
    'url': 'bg-sky-100', 'manual': 'bg-indigo-100', 'policy': 'bg-purple-100',
    'procedure': 'bg-violet-100', 'contract': 'bg-orange-100',
    'faq': 'bg-pink-100', 'other': 'bg-slate-100',
}
_TYPE_BADGE = {
    'pdf': 'bg-red-50 text-red-700', 'word': 'bg-blue-50 text-blue-700',
    'excel': 'bg-emerald-50 text-emerald-700', 'csv': 'bg-teal-50 text-teal-700',
    'text': 'bg-slate-100 text-slate-600', 'json': 'bg-amber-50 text-amber-700',
    'url': 'bg-sky-50 text-sky-700', 'manual': 'bg-indigo-50 text-indigo-700',
    'policy': 'bg-purple-50 text-purple-700', 'procedure': 'bg-violet-50 text-violet-700',
    'contract': 'bg-orange-50 text-orange-700', 'faq': 'bg-pink-50 text-pink-700',
    'other': 'bg-slate-100 text-slate-500',
}
_TYPE_LABEL = {
    'pdf': 'PDF', 'word': 'Word', 'excel': 'Excel', 'csv': 'CSV',
    'text': 'نص', 'json': 'JSON', 'url': 'رابط', 'manual': 'دليل',
    'policy': 'سياسة', 'procedure': 'إجراء', 'contract': 'عقد',
    'faq': 'أسئلة شائعة', 'other': 'أخرى',
}

_PDF_ICON = '<svg class="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM9.5 17.5H8v-5h1.5c1.1 0 1.8.7 1.8 2.5s-.7 2.5-1.8 2.5zm0-4H9v3h.5c.6 0 .8-.5.8-1.5s-.2-1.5-.8-1.5zm3.5 4h-1v-5h1c1.2 0 2 .8 2 2.5s-.8 2.5-2 2.5zm0-4h-.1v3H13c.6 0 1-.4 1-1.5s-.4-1.5-1-1.5zm4 0h-1.5v1h1.3v1h-1.3v2H15v-5h2v1z"/></svg>'
_WORD_ICON = '<svg class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM8 17l1.5-5 1.5 4 1.5-4L14 17h-1l-1-3-1 3H8z"/></svg>'
_EXCEL_ICON = '<svg class="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM8 13l2 2-2 2h1.5l1.5-1.5L12.5 17H14l-2-2 2-2h-1.5L11 14.5 9.5 13H8z"/></svg>'
_DEFAULT_ICON = '<svg class="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>'
_TYPE_ICONS = {
    'pdf': _PDF_ICON, 'word': _WORD_ICON, 'excel': _EXCEL_ICON,
    'csv': _EXCEL_ICON.replace('emerald', 'teal'),
}

templates.env.globals['doc_type_bg'] = lambda dt: _TYPE_BG.get(str(dt), 'bg-slate-100')
templates.env.globals['type_badge_class'] = lambda dt: _TYPE_BADGE.get(str(dt), 'bg-slate-100 text-slate-500')
templates.env.globals['doc_type_label'] = lambda dt: _TYPE_LABEL.get(str(dt), str(dt))
templates.env.globals['doc_type_icon'] = lambda dt: _TYPE_ICONS.get(str(dt), _DEFAULT_ICON)

router = APIRouter(tags=["Web"])

COOKIE_NAME = "access_token"


# ══════════════════════════════════════════════════════════════════════════════
# ⚠️  ملاحظة مهمة حول ترتيب تسجيل /youtube:
# يوجد تعريفان لـ /youtube:
#   1. youtube_web_router (من app/domains/youtube/web.py) — يعرض youtube.html
#      مع tracked_queries_json و api_key_set ✅
#   2. youtube_page (في الأسفل في هذا الملف) — تعريف قديم بدون هذه المتغيرات ❌
#
# FastAPI يستخدم آخر تعريف مسجَّل. لذا نُسجّل youtube_web_router هنا أولًا
# ثم نُعيد تسجيله في نهاية الملف ليفوز.
# ══════════════════════════════════════════════════════════════════════════════

router.include_router(youtube_web_router)


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


def _is_https(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto", "")
    return proto == "https" or str(request.url).startswith("https")


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
                "login.html", {"request": request, "error": "بيانات الدخول غير صحيحة"},
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
            {"request": request, "error": f"خطأ في الخادم، يرجى المحاولة لاحقاً"},
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
    """Lightweight cookie-based session check for the back-button guard."""
    user = get_current_user_from_cookie(request, db)
    if not user:
        from fastapi.responses import JSONResponse
        return JSONResponse({"authenticated": False}, status_code=401)
    from fastapi.responses import JSONResponse
    return JSONResponse({"authenticated": True})


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
    total_docs = len(documents)
    try:
        trained_docs = sum(1 for d in documents if d.is_trained)
    except Exception:
        trained_docs = 0
    processing_docs = sum(1 for d in documents if d.status == kb_models.KnowledgeStatus.PROCESSING)
    active_docs = sum(1 for d in documents if d.status == kb_models.KnowledgeStatus.ACTIVE)
    return templates.TemplateResponse("knowledge.html", {
        "request": request, "user": user, "documents": documents,
        "categories": categories, "page": "knowledge",
        "stats": {
            "total": total_docs,
            "trained": trained_docs,
            "processing": processing_docs,
            "active": active_docs,
            "categories": len(categories),
        }
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

    tg_account = db.query(tg_models.TelegramAccount).first()
    tg_market = tg_account.market_analysis if tg_account and tg_account.market_analysis else None
    tg_market_at = (tg_account.market_analysis_at.strftime("%Y-%m-%d %H:%M") if tg_account and tg_account.market_analysis_at else None)
    tg_total_msgs = db.query(tg_models.TelegramMessage).count() if tg_account else 0

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
        "tg_market": tg_market,
        "tg_market_at": tg_market_at,
        "tg_total_msgs": tg_total_msgs,
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


# ─── TELEGRAM ─────────────────────────────────────────────────────────────────

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
        account = None
        messages = []
        rules = []

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
        "messages_json": json.dumps([msg_to_dict(m) for m in messages], ensure_ascii=False),
        "rules_json": json.dumps([rule_to_dict(r) for r in rules], ensure_ascii=False),
    })


# ─── WHATSAPP ─────────────────────────────────────────────────────────────────

@router.get("/whatsapp", response_class=HTMLResponse)
def whatsapp_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    account = None
    messages = []
    rules = []
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
    except Exception:
        pass

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
        "messages_json": json.dumps([msg_to_dict(m) for m in messages], ensure_ascii=False),
        "rules_json": json.dumps([rule_to_dict(r) for r in rules], ensure_ascii=False),
    })


# ─── FACEBOOK ─────────────────────────────────────────────────────────────────

@router.get("/facebook", response_class=HTMLResponse)
def facebook_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    account = None
    messages = []
    rules = []
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
    except Exception:
        pass

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
        "messages_json": json.dumps([msg_to_dict(m) for m in messages], ensure_ascii=False),
        "rules_json": json.dumps([rule_to_dict(r) for r in rules], ensure_ascii=False),
    })


# ─── INSTAGRAM ────────────────────────────────────────────────────────────────

@router.get("/instagram", response_class=HTMLResponse)
def instagram_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    account = None
    messages = []
    rules = []
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
    except Exception:
        pass

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
        "messages_json": json.dumps([msg_to_dict(m) for m in messages], ensure_ascii=False),
        "rules_json": json.dumps([rule_to_dict(r) for r in rules], ensure_ascii=False),
    })


# ─── REDDIT ───────────────────────────────────────────────────────────────────

@router.get("/reddit", response_class=HTMLResponse)
def reddit_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    account = None
    posts = []
    comments = []
    rules = []
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
    except Exception:
        pass

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
        "posts_json": json.dumps([post_to_dict(p) for p in posts], ensure_ascii=False),
        "rules_json": json.dumps([rule_to_dict(r) for r in rules], ensure_ascii=False),
    })


# ─── TIKTOK ───────────────────────────────────────────────────────────────────

@router.get("/tiktok", response_class=HTMLResponse)
def tiktok_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    account = None
    videos = []
    comments = []
    rules = []
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
    except Exception:
        pass

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
        "videos_json": json.dumps([video_to_dict(v) for v in videos], ensure_ascii=False),
        "rules_json": json.dumps([rule_to_dict(r) for r in rules], ensure_ascii=False),
    })


# ─── YOUTUBE (قديم — يُتجاوز بواسطة youtube_web_router في نهاية الملف) ───────
# ⚠️  هذا تعريف قديم يستخدم YouTubeAccount/YouTubeVideo غير موجودين.
#     نُبقيه لتفادي كسر أي كود قد يعتمد عليه، لكن youtube_web_router
#     (المُعاد تسجيله في نهاية الملف) سيتجاوزه.

@router.get("/youtube", response_class=HTMLResponse)
def youtube_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    account = None
    videos = []
    comments = []
    rules = []
    try:
        from app.domains.youtube import models as yt_models
        account = db.query(yt_models.YouTubeAccount).first()
        if account:
            videos = db.query(yt_models.YouTubeVideo)\
                .filter_by(account_id=account.id)\
                .order_by(yt_models.YouTubeVideo.created_at.desc())\
                .limit(200).all()
            comments = db.query(yt_models.YouTubeComment)\
                .filter_by(account_id=account.id)\
                .order_by(yt_models.YouTubeComment.created_at.desc())\
                .limit(200).all()
            rules = db.query(yt_models.YouTubeReplyRule)\
                .filter_by(account_id=account.id).all()
    except Exception:
        pass

    def video_to_dict(v):
        return {
            "id": v.id,
            "video_id": getattr(v, "video_id", ""),
            "title": getattr(v, "title", "") or "",
            "description": getattr(v, "description", "") or "",
            "channel_title": getattr(v, "channel_title", "") or "",
            "views": getattr(v, "views", 0),
            "likes": getattr(v, "likes", 0),
            "comments_count": getattr(v, "comments_count", 0),
            "duration": getattr(v, "duration", "") or "",
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

    return templates.TemplateResponse("youtube.html", {
        "request": request,
        "user": user,
        "page": "youtube",
        "account": account,
        "videos": videos,
        "comments": comments,
        "videos_json": json.dumps([video_to_dict(v) for v in videos], ensure_ascii=False),
        "rules_json": json.dumps([rule_to_dict(r) for r in rules], ensure_ascii=False),
    })


# ─── YOUTUBE OPPORTUNITIES ────────────────────────────────────────────────────

@router.get("/youtube/opportunities", response_class=HTMLResponse)
def youtube_opportunities_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("youtube_opportunities.html", {
        "request": request,
        "user": user,
        "page": "youtube-opportunities",
    })


# ─── GOOGLE TRENDS ────────────────────────────────────────────────────────────

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
    except Exception:
        pass

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
        "trends_json": json.dumps([trend_to_dict(t) for t in trends], ensure_ascii=False),
        "interest_over_time_json": json.dumps(interest_over_time, ensure_ascii=False),
        "related_queries_json": json.dumps(related_queries, ensure_ascii=False),
    })


# ─── API Settings ───────────────────────────────────────────────────────────────

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
        "request":   request,
        "user":      user,
        "page":      "api-settings",
        "keys":      keys_data,
        "keys_json": json.dumps(keys_data, ensure_ascii=False),
    })


# ══════════════════════════════════════════════════════════════════════════════
# ⚠️  إعادة تسجيل youtube_web_router في النهاية ليتجاوز youtube_page القديم
# ══════════════════════════════════════════════════════════════════════════════
#router.include_router(youtube_web_router)
