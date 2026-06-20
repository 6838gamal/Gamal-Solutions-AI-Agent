import asyncio
import logging
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domains.telegram import models as tg_models, service as tg_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/connect/request-code")
async def request_code(
    api_id: str = Form(...),
    api_hash: str = Form(...),
    phone: str = Form(...),
    db: Session = Depends(get_db),
):
    account = tg_service.get_or_create_account(db)
    try:
        session_str, phone_code_hash = await tg_service._send_code(int(api_id), api_hash, phone)
        tg_service.save_code_request(db, account, api_id, api_hash, phone, session_str, phone_code_hash)
        return JSONResponse({"success": True, "message": "تم إرسال رمز التحقق إلى هاتفك"})
    except Exception as e:
        logger.error(f"request_code error: {e}")
        tg_service.save_error(db, account, str(e))
        return JSONResponse({"success": False, "message": f"خطأ: {str(e)}"}, status_code=400)


@router.post("/connect/verify-code")
async def verify_code(
    code: str = Form(...),
    db: Session = Depends(get_db),
):
    account = tg_service.get_account(db)
    if not account or account.status != tg_models.TelegramConnectionStatus.PENDING_CODE:
        return JSONResponse({"success": False, "message": "يجب طلب رمز التحقق أولاً"}, status_code=400)
    try:
        new_session, me = await tg_service._sign_in(
            int(account.api_id), account.api_hash,
            account.session_string, account.phone, code, account.phone_code_hash
        )
        tg_service.save_connected(db, account, new_session, me)
        return JSONResponse({"success": True, "message": f"تم الاتصال بنجاح! مرحباً {me.first_name}"})
    except Exception as e:
        logger.error(f"verify_code error: {e}")
        tg_service.save_error(db, account, str(e))
        return JSONResponse({"success": False, "message": f"رمز خاطئ أو منتهي: {str(e)}"}, status_code=400)


@router.post("/connect/validate")
def validate_session(db: Session = Depends(get_db)):
    """Verify the stored session is still alive without re-logging in."""
    account = tg_service.get_account(db)
    if not account or account.status != tg_models.TelegramConnectionStatus.CONNECTED:
        return JSONResponse({"valid": False, "message": "لا توجد جلسة نشطة"})
    ok = tg_service.validate_and_refresh_session(db)
    if ok:
        return JSONResponse({"valid": True, "message": "✅ الجلسة صالحة ومحفوظة في قاعدة البيانات"})
    else:
        db.refresh(account)
        return JSONResponse({"valid": False, "message": account.error_message or "انتهت صلاحية الجلسة"}, status_code=200)


@router.post("/connect/disconnect")
def disconnect(db: Session = Depends(get_db)):
    account = tg_service.get_account(db)
    if account:
        tg_service.disconnect_account(db, account)
    return JSONResponse({"success": True, "message": "تم قطع الاتصال"})


@router.get("/messages/count")
def messages_count(db: Session = Depends(get_db)):
    """Lightweight poll endpoint — returns current message count and unread count."""
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"total": 0, "unread": 0, "connected": False})
    from app.domains.telegram.models import TelegramMessage
    total = db.query(TelegramMessage).filter_by(account_id=account.id).count()
    unread = db.query(TelegramMessage).filter_by(account_id=account.id, is_read=False, direction="incoming").count()
    return JSONResponse({
        "total": total,
        "unread": unread,
        "connected": account.status == tg_models.TelegramConnectionStatus.CONNECTED,
    })


@router.get("/messages/list")
def list_messages(db: Session = Depends(get_db)):
    """Return all messages as JSON for live UI refresh."""
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"messages": []})
    from app.domains.telegram.models import TelegramMessage
    msgs = db.query(TelegramMessage).filter_by(account_id=account.id)\
             .order_by(TelegramMessage.received_at.desc()).limit(500).all()
    def _serialize(m):
        return {
            "id": m.id,
            "chat_id": m.chat_id,
            "chat_title": m.chat_title or "",
            "chat_type": m.chat_type or "",
            "sender_name": m.sender_name or "",
            "sender_username": m.sender_username or "",
            "content": m.content or "",
            "direction": m.direction or "incoming",
            "is_read": m.is_read,
            "is_analyzed": m.is_analyzed,
            "reply_sent": m.reply_sent,
            "analysis_result": m.analysis_result or {},
            "received_at": m.received_at.isoformat() if m.received_at else None,
        }
    return JSONResponse({"messages": [_serialize(m) for m in msgs]})


@router.post("/messages/sync")
def sync_messages(db: Session = Depends(get_db)):
    account = tg_service.get_account(db)
    if not account or account.status != tg_models.TelegramConnectionStatus.CONNECTED:
        return JSONResponse({"success": False, "message": "يجب الاتصال بتيليجرام أولاً"}, status_code=400)
    count = tg_service.sync_messages(db, account)
    return JSONResponse({"success": True, "message": f"تم استيراد {count} رسالة جديدة", "count": count})


@router.post("/messages/analyze")
def analyze_messages(db: Session = Depends(get_db)):
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"success": False, "message": "لا يوجد حساب مربوط"}, status_code=400)
    count = tg_service.analyze_pending(db, account)
    return JSONResponse({"success": True, "message": f"تم تحليل {count} رسالة", "count": count})


@router.post("/analysis/market")
def run_market_analysis(db: Session = Depends(get_db)):
    """Run deep market intelligence analysis on all stored Telegram messages."""
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"success": False, "message": "لا يوجد حساب مربوط"}, status_code=400)
    total_msgs = db.query(tg_models.TelegramMessage).filter_by(account_id=account.id).count()
    if total_msgs == 0:
        return JSONResponse({"success": False, "message": "لا توجد رسائل — اجلب الرسائل أولاً"}, status_code=400)
    result = tg_service.run_market_analysis(db, account)
    return JSONResponse({"success": True, "result": result, "message": f"تم تحليل {total_msgs} رسالة بنجاح"})


@router.get("/analysis/market")
def get_market_analysis(db: Session = Depends(get_db)):
    """Get the last stored market intelligence report."""
    account = tg_service.get_account(db)
    if not account or not account.market_analysis:
        return JSONResponse({"has_data": False, "result": None})
    return JSONResponse({
        "has_data": True,
        "result": account.market_analysis,
        "analyzed_at": account.market_analysis_at.isoformat() if account.market_analysis_at else None,
    })


@router.post("/messages/{message_id}/reply")
def send_reply(
    message_id: int,
    reply_text: str = Form(...),
    db: Session = Depends(get_db),
):
    account = tg_service.get_account(db)
    if not account or account.status != tg_models.TelegramConnectionStatus.CONNECTED:
        return JSONResponse({"success": False, "message": "يجب الاتصال بتيليجرام أولاً"}, status_code=400)
    ok, msg = tg_service.send_reply(db, account, message_id, reply_text)
    return JSONResponse({"success": ok, "message": msg})


@router.post("/messages/{message_id}/mark-read")
def mark_read(message_id: int, db: Session = Depends(get_db)):
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"success": False}, status_code=400)
    msg = db.query(tg_models.TelegramMessage).filter_by(id=message_id, account_id=account.id).first()
    if msg:
        msg.is_read = True
        db.commit()
    return JSONResponse({"success": True})


@router.get("/rules")
def list_rules(db: Session = Depends(get_db)):
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"rules": []})
    rules = db.query(tg_models.TelegramReplyRule).filter_by(account_id=account.id).all()
    return JSONResponse({"rules": [
        {
            "id": r.id, "rule_name": r.rule_name, "is_active": r.is_active,
            "target_type": r.target_type, "keywords": r.keywords,
            "reply_mode": r.reply_mode, "reply_template": r.reply_template,
            "replies_sent": r.replies_sent,
        } for r in rules
    ]})


@router.post("/rules")
def create_rule(
    rule_name: str = Form(...),
    target_type: str = Form("all"),
    target_chat_id: str = Form(""),
    target_sender_username: str = Form(""),
    keywords: str = Form(""),
    reply_mode: str = Form("manual"),
    reply_template: str = Form(""),
    reply_delay_seconds: int = Form(0),
    max_replies_per_hour: int = Form(10),
    db: Session = Depends(get_db),
):
    account = tg_service.get_or_create_account(db)
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
    rule = tg_models.TelegramReplyRule(
        account_id=account.id,
        rule_name=rule_name,
        target_type=target_type,
        target_chat_id=target_chat_id or None,
        target_sender_username=target_sender_username or None,
        keywords=kw_list,
        reply_mode=reply_mode,
        reply_template=reply_template or None,
        reply_delay_seconds=reply_delay_seconds,
        max_replies_per_hour=max_replies_per_hour,
    )
    db.add(rule)
    db.commit()
    return JSONResponse({"success": True, "message": "تمت إضافة القاعدة بنجاح"})


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"success": False}, status_code=400)
    rule = db.query(tg_models.TelegramReplyRule).filter_by(id=rule_id, account_id=account.id).first()
    if rule:
        db.delete(rule)
        db.commit()
    return JSONResponse({"success": True})


@router.post("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    account = tg_service.get_account(db)
    if not account:
        return JSONResponse({"success": False}, status_code=400)
    rule = db.query(tg_models.TelegramReplyRule).filter_by(id=rule_id, account_id=account.id).first()
    if rule:
        rule.is_active = not rule.is_active
        db.commit()
    return JSONResponse({"success": True, "is_active": rule.is_active if rule else False})
