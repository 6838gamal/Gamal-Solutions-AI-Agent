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
    for m in msgs:
        existing = db.query(TelegramMessage).filter_by(
            account_id=account.id,
            message_id=m["message_id"],
            chat_id=m["chat_id"]
        ).first()
        if not existing:
            msg = TelegramMessage(
                account_id=account.id,
                **m
            )
            db.add(msg)
            count += 1
    db.commit()
    return count


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

    return {
        "sentiment": sentiment,
        "intent": intent,
        "priority": priority,
        "keywords": list(set(keywords)),
        "word_count": len(content.split()) if content else 0,
        "char_count": len(content) if content else 0,
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
