"""
Public REST API — مصادقة بمفتاح API (X-API-Key)
Base: /api/public/v1
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.api_key_auth import get_api_key, require_permission
from app.domains.api_keys.models import APIKey

router = APIRouter()

# ─── Docs ──────────────────────────────────────────────────────────────────────

@router.get("/", tags=["Public API"])
def api_info():
    return {
        "name": "جمال سولوشنز — Public API",
        "version": "1.0",
        "auth": "Header: X-API-Key: <your_key>",
        "endpoints": {
            "GET  /api/public/v1/messages":              "تدفق موحد للرسائل (تيليجرام + واتساب)",
            "GET  /api/public/v1/telegram/messages":     "رسائل تيليجرام",
            "GET  /api/public/v1/telegram/analysis":     "تقرير ذكاء السوق",
            "GET  /api/public/v1/customers":             "العملاء والمتابعون",
            "GET  /api/public/v1/conversations":         "المحادثات",
            "GET  /api/public/v1/analytics":             "ملخص التحليلات",
            "POST /api/public/v1/events/inbound":        "استقبال بيانات من مصادر خارجية",
        },
    }


# ─── Unified Message Stream ────────────────────────────────────────────────────

@router.get("/messages", tags=["Messages"])
def unified_messages(
    channel: str = Query(None, description="telegram | whatsapp | all"),
    limit:   int = Query(100, le=500),
    offset:  int = Query(0),
    api_key: APIKey = Depends(require_permission("messages:read")),
    db: Session = Depends(get_db),
):
    """Unified message feed from all connected channels."""
    results = []

    # ── Telegram ──────────────────────────────────────────────────────────────
    if not channel or channel in ("all", "telegram"):
        try:
            from app.domains.telegram.models import TelegramMessage, TelegramAccount
            account = db.query(TelegramAccount).first()
            if account:
                q = db.query(TelegramMessage).filter_by(account_id=account.id)
                msgs = q.order_by(TelegramMessage.received_at.desc()).offset(offset).limit(limit).all()
                for m in msgs:
                    results.append({
                        "id":          f"tg_{m.id}",
                        "channel":     "telegram",
                        "direction":   m.direction,
                        "sender_name": m.sender_name,
                        "sender_username": m.sender_username,
                        "chat_title":  m.chat_title,
                        "chat_type":   m.chat_type,
                        "content":     m.content,
                        "is_read":     m.is_read,
                        "analysis":    m.analysis_result or {},
                        "received_at": m.received_at.isoformat() if m.received_at else None,
                    })
        except Exception:
            pass

    results.sort(key=lambda x: x.get("received_at") or "", reverse=True)
    return {"total": len(results), "messages": results[:limit]}


# ─── Telegram ─────────────────────────────────────────────────────────────────

@router.get("/telegram/messages", tags=["Telegram"])
def telegram_messages(
    direction: str = Query(None, description="incoming | outgoing"),
    chat_id:   str = Query(None),
    limit:     int = Query(100, le=500),
    offset:    int = Query(0),
    api_key: APIKey = Depends(require_permission("telegram:read")),
    db: Session = Depends(get_db),
):
    from app.domains.telegram.models import TelegramMessage, TelegramAccount
    account = db.query(TelegramAccount).first()
    if not account:
        return JSONResponse({"total": 0, "messages": []})
    q = db.query(TelegramMessage).filter_by(account_id=account.id)
    if direction:
        q = q.filter(TelegramMessage.direction == direction)
    if chat_id:
        q = q.filter(TelegramMessage.chat_id == chat_id)
    total = q.count()
    msgs  = q.order_by(TelegramMessage.received_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "messages": [
            {
                "id":           m.id,
                "message_id":   m.message_id,
                "chat_id":      m.chat_id,
                "chat_title":   m.chat_title,
                "chat_type":    m.chat_type,
                "direction":    m.direction,
                "sender_name":  m.sender_name,
                "sender_username": m.sender_username,
                "content":      m.content,
                "is_read":      m.is_read,
                "is_analyzed":  m.is_analyzed,
                "analysis":     m.analysis_result or {},
                "received_at":  m.received_at.isoformat() if m.received_at else None,
            }
            for m in msgs
        ],
    }


@router.get("/telegram/analysis", tags=["Telegram"])
def telegram_market_analysis(
    api_key: APIKey = Depends(require_permission("telegram:read")),
    db: Session = Depends(get_db),
):
    from app.domains.telegram.models import TelegramAccount
    account = db.query(TelegramAccount).first()
    if not account or not account.market_analysis:
        return JSONResponse({"has_data": False, "result": None})
    return {
        "has_data":    True,
        "analyzed_at": account.market_analysis_at.isoformat() if account.market_analysis_at else None,
        "result":      account.market_analysis,
    }


# ─── Customers / CRM ──────────────────────────────────────────────────────────

@router.get("/customers", tags=["CRM"])
def customers(
    status: str = Query(None),
    source: str = Query(None, description="telegram | whatsapp | manual"),
    limit:  int = Query(100, le=500),
    offset: int = Query(0),
    api_key: APIKey = Depends(require_permission("customers:read")),
    db: Session = Depends(get_db),
):
    from app.domains.customers.models import Customer
    q = db.query(Customer)
    if status:
        q = q.filter(Customer.status == status)
    if source == "telegram":
        q = q.filter(Customer.email.like("%@telegram.local"))
    elif source == "whatsapp":
        q = q.filter(Customer.email.like("%@whatsapp.local"))
    total = q.count()
    rows  = q.order_by(Customer.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "customers": [
            {
                "id":      c.id,
                "name":    c.name,
                "email":   c.email,
                "phone":   c.phone,
                "company": c.company,
                "status":  c.status,
                "score":   c.score,
                "tags":    c.tags or [],
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in rows
        ],
    }


# ─── Conversations ─────────────────────────────────────────────────────────────

@router.get("/conversations", tags=["Conversations"])
def conversations(
    channel: str = Query(None, description="telegram | whatsapp | web"),
    status:  str = Query(None),
    limit:   int = Query(50, le=200),
    offset:  int = Query(0),
    api_key: APIKey = Depends(require_permission("conversations:read")),
    db: Session = Depends(get_db),
):
    from app.domains.conversations.models import Conversation, Message
    q = db.query(Conversation)
    if channel:
        q = q.filter(Conversation.channel == channel)
    if status:
        q = q.filter(Conversation.status == status)
    total = q.count()
    rows  = q.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "conversations": [
            {
                "id":         c.id,
                "channel":    c.channel,
                "status":     c.status,
                "subject":    c.subject,
                "priority":   c.priority,
                "customer_id": c.customer_id,
                "msg_count":  len(c.messages),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in rows
        ],
    }


# ─── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics", tags=["Analytics"])
def analytics_summary(
    api_key: APIKey = Depends(require_permission("analytics:read")),
    db: Session = Depends(get_db),
):
    from app.domains.customers.models import Customer
    from app.domains.conversations.models import Conversation
    from app.domains.telegram.models import TelegramMessage, TelegramAccount

    customers_total = db.query(Customer).count()
    convs_total     = db.query(Conversation).count()
    convs_open      = db.query(Conversation).filter(Conversation.status == "open").count()

    tg_total = 0
    tg_unread = 0
    try:
        account = db.query(TelegramAccount).first()
        if account:
            tg_total  = db.query(TelegramMessage).filter_by(account_id=account.id).count()
            tg_unread = db.query(TelegramMessage).filter_by(account_id=account.id, is_read=False).count()
    except Exception:
        pass

    return {
        "generated_at":       datetime.utcnow().isoformat(),
        "customers":          {"total": customers_total},
        "conversations":      {"total": convs_total, "open": convs_open},
        "telegram":           {"total_messages": tg_total, "unread": tg_unread},
    }


# ─── Inbound Webhook ──────────────────────────────────────────────────────────

@router.post("/events/inbound", tags=["Webhook"])
async def inbound_event(
    request,
    api_key: APIKey = Depends(require_permission("events:write")),
    db: Session = Depends(get_db),
):
    """Receive inbound events from external systems (WhatsApp, CRM, etc.)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid JSON"}, status_code=400)

    channel  = body.get("channel", "unknown")
    sender   = body.get("sender_name", "مجهول")
    content  = body.get("content", "")
    chat_id  = body.get("chat_id", "external")
    meta     = body.get("metadata", {})

    if channel == "whatsapp" and content:
        _process_whatsapp_message(db, sender, content, chat_id, meta)

    return JSONResponse({
        "success": True,
        "message": f"تم استلام الحدث من القناة: {channel}",
        "channel": channel,
        "received_at": datetime.utcnow().isoformat(),
    })


def _process_whatsapp_message(db, sender_name, content, chat_id, meta):
    """Store inbound WhatsApp message into Conversations + CRM."""
    try:
        from app.domains.customers.models import Customer, CustomerStatus
        from app.domains.conversations.models import Conversation, Message, Channel, ConversationStatus, MessageRole

        virtual_email = f"wa_{chat_id}@whatsapp.local"
        customer = db.query(Customer).filter_by(email=virtual_email).first()
        if not customer:
            customer = Customer(
                name=sender_name,
                email=virtual_email,
                tags=["whatsapp"],
                status=CustomerStatus.LEAD,
                notes="أضيف تلقائياً من WhatsApp",
            )
            db.add(customer)
            db.flush()

        conv = db.query(Conversation).filter(
            Conversation.customer_id == customer.id,
            Conversation.channel == Channel.WHATSAPP,
        ).first()
        if not conv:
            conv = Conversation(
                customer_id=customer.id,
                channel=Channel.WHATSAPP,
                subject=f"WhatsApp — {sender_name}",
                status=ConversationStatus.OPEN,
            )
            db.add(conv)
            db.flush()

        msg = Message(
            conversation_id=conv.id,
            role=MessageRole.USER,
            content=content,
            metadata_extra=meta,
        )
        db.add(msg)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[WhatsApp inbound] خطأ: {e}")
