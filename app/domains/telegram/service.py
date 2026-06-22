import asyncio
import logging
import threading
from typing import Optional
from sqlalchemy.orm import Session
from app.domains.telegram.models import TelegramAccount, TelegramMessage, TelegramReplyRule, TelegramConnectionStatus

logger = logging.getLogger(__name__)

# Global listener state
_listener_thread: Optional[threading.Thread] = None
_listener_loop: Optional[asyncio.AbstractEventLoop] = None
_listener_client = None
_listener_running = False


def get_account(db: Session) -> Optional[TelegramAccount]:
    return db.query(TelegramAccount).first()


def get_or_create_account(db: Session) -> TelegramAccount:
    acc = db.query(TelegramAccount).first()
    if not acc:
        acc = TelegramAccount(status=TelegramConnectionStatus.DISCONNECTED)
        db.add(acc)
        db.commit()
        db.refresh(acc)
    return acc


async def _send_code(api_id: int, api_hash: str, phone: str):
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    result = await client.send_code_request(phone)
    session_str = client.session.save()
    await client.disconnect()
    return session_str, result.phone_code_hash


async def _sign_in(api_id: int, api_hash: str, session_str: str, phone: str, code: str, phone_code_hash: str):
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
    me = await client.get_me()
    new_session = client.session.save()
    await client.disconnect()
    return new_session, me


async def _get_recent_messages(api_id: int, api_hash: str, session_str: str, limit: int = 50):
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.types import User, Chat, Channel
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    messages_data = []
    try:
        dialogs = await client.get_dialogs(limit=20)
        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, User) and entity.is_self:
                continue
            chat_id = str(dialog.id)
            chat_title = dialog.name or "بدون اسم"
            if isinstance(entity, User):
                chat_type = "user"
            elif isinstance(entity, Channel):
                chat_type = "channel" if entity.broadcast else "group"
            else:
                chat_type = "group"
            msgs = await client.get_messages(entity, limit=10)
            for msg in msgs:
                if not msg.message:
                    continue
                sender_name = "مجهول"
                sender_id = ""
                sender_username = ""
                if msg.sender:
                    s = msg.sender
                    sender_id = str(s.id)
                    if isinstance(s, User):
                        sender_name = (s.first_name or "") + " " + (s.last_name or "")
                        sender_name = sender_name.strip() or "مجهول"
                        sender_username = s.username or ""
                messages_data.append({
                    "message_id": msg.id,
                    "chat_id": chat_id,
                    "chat_title": chat_title,
                    "chat_type": chat_type,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "sender_username": sender_username,
                    "content": msg.message or "",
                    "received_at": msg.date,
                    "direction": "incoming" if not msg.out else "outgoing",
                })
    finally:
        await client.disconnect()
    return messages_data


async def _send_reply(api_id: int, api_hash: str, session_str: str, chat_id: str, message: str):
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.connect()
    try:
        await client.send_message(int(chat_id), message)
    finally:
        await client.disconnect()


def save_code_request(db: Session, account: TelegramAccount, api_id: str, api_hash: str,
                       phone: str, session_str: str, phone_code_hash: str):
    account.api_id = api_id
    account.api_hash = api_hash
    account.phone = phone
    account.session_string = session_str
    account.phone_code_hash = phone_code_hash
    account.status = TelegramConnectionStatus.PENDING_CODE
    account.error_message = None
    db.commit()


def save_connected(db: Session, account: TelegramAccount, session_str: str, me):
    account.session_string = session_str
    account.status = TelegramConnectionStatus.CONNECTED
    account.telegram_user_id = str(me.id)
    account.telegram_username = me.username or ""
    account.telegram_first_name = me.first_name or ""
    account.phone_code_hash = None
    account.error_message = None
    db.commit()


def save_error(db: Session, account: TelegramAccount, error: str):
    account.status = TelegramConnectionStatus.ERROR
    account.error_message = error
    db.commit()


async def _validate_session(api_id: int, api_hash: str, session_str: str) -> tuple[bool, str]:
    """Try to connect with stored session and confirm it's still valid."""
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "الجلسة منتهية الصلاحية"
        me = await client.get_me()
        new_session = client.session.save()
        await client.disconnect()
        return True, new_session
    except Exception as e:
        return False, str(e)


def validate_and_refresh_session(db: Session) -> bool:
    """
    Called on startup — checks stored session is still valid.
    Updates status in DB accordingly.
    Returns True if session is valid.
    """
    account = db.query(TelegramAccount).first()
    if not account or account.status != TelegramConnectionStatus.CONNECTED:
        return False
    if not account.session_string or not account.api_id or not account.api_hash:
        save_error(db, account, "بيانات الجلسة ناقصة")
        return False
    loop = asyncio.new_event_loop()
    try:
        ok, result = loop.run_until_complete(
            _validate_session(int(account.api_id), account.api_hash, account.session_string)
        )
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        ok, result = False, str(e)
    finally:
        loop.close()
    if ok:
        account.session_string = result  # refresh with latest saved session
        account.error_message = None
        db.commit()
        logger.info("✅ Telegram session is valid and refreshed")
        return True
    else:
        account.status = TelegramConnectionStatus.ERROR
        account.error_message = f"انتهت صلاحية الجلسة: {result}"
        db.commit()
        logger.warning(f"⚠️ Telegram session invalid: {result}")
        return False


def disconnect_account(db: Session, account: TelegramAccount):
    account.status = TelegramConnectionStatus.DISCONNECTED
    account.session_string = None
    account.phone_code_hash = None
    account.telegram_user_id = None
    account.telegram_username = None
    account.telegram_first_name = None
    account.error_message = None
    db.commit()


def sync_messages(db: Session, account: TelegramAccount):
    if account.status != TelegramConnectionStatus.CONNECTED:
        return 0
    loop = asyncio.new_event_loop()
    try:
        msgs = loop.run_until_complete(_get_recent_messages(
            int(account.api_id), account.api_hash, account.session_string
        ))
    except Exception as e:
        logger.error(f"Telegram sync error: {e}")
        return 0
    finally:
        loop.close()
    count = 0
    new_msgs = []
    for m in msgs:
        existing = db.query(TelegramMessage).filter_by(
            account_id=account.id,
            message_id=m["message_id"],
            chat_id=m["chat_id"]
        ).first()
        if not existing:
            msg = TelegramMessage(account_id=account.id, **m)
            db.add(msg)
            new_msgs.append(m)
            count += 1
    db.commit()

    # ── تدفق البيانات: تيليجرام → CRM + المحادثات ─────────────────────────
    for m in new_msgs:
        if m.get("direction") == "incoming" and m.get("sender_name"):
            try:
                _flow_to_crm_and_conversations(db, m)
            except Exception as fe:
                logger.warning(f"[DataFlow] خطأ في تدفق البيانات: {fe}")

    return count


def _flow_to_crm_and_conversations(db: Session, m: dict):
    """تدفق رسالة تيليجرام → CRM (Customer) + المحادثات (Conversation + Message)."""
    from app.domains.customers.models import Customer, CustomerStatus
    from app.domains.conversations.models import (
        Conversation, Message, Channel, ConversationStatus, MessageRole
    )

    sender_name     = m.get("sender_name", "مجهول")
    sender_username = m.get("sender_username", "")
    chat_id         = str(m.get("chat_id", ""))
    chat_title      = m.get("chat_title", sender_name)
    content         = m.get("content", "")
    if not content:
        return

    # ── 1. Upsert Customer ──────────────────────────────────────────────────
    virtual_email = (
        f"tg_{sender_username}@telegram.local"
        if sender_username
        else f"tg_id_{hash(sender_name) % 999999}@telegram.local"
    )
    customer = db.query(Customer).filter_by(email=virtual_email).first()
    if not customer:
        customer = Customer(
            name=sender_name,
            email=virtual_email,
            tags=["telegram"],
            status=CustomerStatus.LEAD,
            notes=f"أضيف تلقائياً من تيليجرام | القناة: {chat_title}",
        )
        db.add(customer)
        db.flush()

    # ── 2. Upsert Conversation (per chat_id) ────────────────────────────────
    conv = db.query(Conversation).filter(
        Conversation.customer_id == customer.id,
        Conversation.channel == Channel.TELEGRAM,
        Conversation.subject.like(f"%[tg:{chat_id}]%"),
    ).first()
    if not conv:
        conv = Conversation(
            customer_id=customer.id,
            channel=Channel.TELEGRAM,
            subject=f"{chat_title} [tg:{chat_id}]",
            status=ConversationStatus.OPEN,
            tags=["telegram"],
        )
        db.add(conv)
        db.flush()

    # ── 3. Add Message ──────────────────────────────────────────────────────
    msg_obj = Message(
        conversation_id=conv.id,
        role=MessageRole.USER,
        content=content,
        metadata_extra={
            "source":           "telegram",
            "chat_id":          chat_id,
            "sender_username":  sender_username,
        },
    )
    db.add(msg_obj)
    db.commit()


def run_market_analysis(db: Session, account: TelegramAccount) -> dict:
    """Run deep market intelligence analysis on all stored messages."""
    from app.domains.telegram.analyzer import run_deep_analysis
    msgs = db.query(TelegramMessage).filter_by(account_id=account.id).all()
    msg_dicts = []
    for m in msgs:
        msg_dicts.append({
            "id": m.id,
            "content": m.content or "",
            "direction": m.direction,
            "chat_title": m.chat_title,
            "chat_type": m.chat_type,
            "sender_name": m.sender_name,
            "received_at": m.received_at.isoformat() if m.received_at else None,
            "analysis_result": m.analysis_result or {},
            "is_analyzed": m.is_analyzed,
        })
    result = run_deep_analysis(msg_dicts)
    account.market_analysis = result
    account.market_analysis_at = __import__("datetime").datetime.utcnow()
    db.commit()
    return result


def analyze_message(content: str) -> dict:
    content_lower = content.lower() if content else ""
    sentiment = "محايد"
    intent = "عام"
    priority = "عادي"
    keywords = []

    positive_words = ["شكر", "ممتاز", "رائع", "جيد", "موافق", "نعم", "بالتوفيق"]
    negative_words = ["مشكلة", "خطأ", "سيء", "لا", "رفض", "شكوى", "معطل"]
    sales_words = ["سعر", "تكلفة", "شراء", "منتج", "عرض", "خصم", "توفر"]
    support_words = ["مساعدة", "دعم", "مشكلة", "حل", "كيف", "لماذا"]

    for w in positive_words:
        if w in content:
            sentiment = "إيجابي"
            keywords.append(w)
    for w in negative_words:
        if w in content:
            sentiment = "سلبي"
            priority = "عالي"
            keywords.append(w)
    for w in sales_words:
        if w in content:
            intent = "مبيعات"
            keywords.append(w)
    for w in support_words:
        if w in content:
            intent = "دعم فني"
            keywords.append(w)

    if "؟" in content or "?" in content:
        intent = "استفسار"

    # ── Signal Type Detection (master prompt classification) ──────────────────
    buying_kw  = ["اشتري","أشتري","سعر","بكم","كم تكلفة","كم الثمن","buy","price","purchase","order","pay"]
    opp_kw     = ["أريد","أبغى","أحتاج","محتاج","ابغى","need","want","looking for","searching"]
    gap_kw     = ["ما في","لا يوجد","ما وجدت","ما لقيت","غير متوفر","not available","can't find","don't know"]
    hidden_kw  = ["لو كان","أتمنى","نتمنى","لو يوجد","wish","would be nice","if only","يا ريت"]
    pain_kw    = ["مشكلة","خطأ","لا يعمل","تعبت","problem","issue","broken","frustrated"]

    signal_type = "مؤشر عام"
    signal_color = "slate"
    if any(k in content_lower for k in buying_kw):
        signal_type  = "إشارة شراء 🛒"
        signal_color = "emerald"
    elif any(k in content_lower for k in opp_kw):
        signal_type  = "إشارة فرصة 🎯"
        signal_color = "blue"
    elif any(k in content_lower for k in gap_kw):
        signal_type  = "ثغرة سوقية 🕳️"
        signal_color = "red"
    elif any(k in content_lower for k in hidden_kw):
        signal_type  = "طلب ضمني 💡"
        signal_color = "purple"
    elif any(k in content_lower for k in pain_kw):
        signal_type  = "نقطة ألم ⚠️"
        signal_color = "orange"

    return {
        "sentiment":   sentiment,
        "intent":      intent,
        "priority":    priority,
        "keywords":    list(set(keywords)),
        "word_count":  len(content.split()) if content else 0,
        "char_count":  len(content) if content else 0,
        "signal_type": signal_type,
        "signal_color": signal_color,
    }


def analyze_pending(db: Session, account: TelegramAccount):
    msgs = db.query(TelegramMessage).filter_by(account_id=account.id, is_analyzed=False).all()
    for m in msgs:
        m.analysis_result = analyze_message(m.content)
        m.is_analyzed = True
    db.commit()
    return len(msgs)


def send_reply(db: Session, account: TelegramAccount, message_id: int, reply_text: str):
    msg = db.query(TelegramMessage).filter_by(id=message_id, account_id=account.id).first()
    if not msg:
        return False, "الرسالة غير موجودة"
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_send_reply(
            int(account.api_id), account.api_hash,
            account.session_string, msg.chat_id, reply_text
        ))
        msg.reply_sent = True
        msg.replied_at = __import__("datetime").datetime.utcnow()
        db.commit()
        return True, "تم إرسال الرد بنجاح"
    except Exception as e:
        logger.error(f"Send reply error: {e}")
        return False, str(e)
    finally:
        loop.close()
