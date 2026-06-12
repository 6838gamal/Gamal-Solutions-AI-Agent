from datetime import datetime
from pydantic import BaseModel
from app.domains.conversations.models import Channel, ConversationStatus, MessageRole


class MessageBase(BaseModel):
    role: MessageRole
    content: str


class MessageCreate(MessageBase):
    pass


class MessageOut(MessageBase):
    id: int
    conversation_id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    customer_id: int | None = None
    channel: Channel = Channel.WEB
    subject: str | None = None
    priority: str = "normal"
    tags: list = []


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    status: ConversationStatus | None = None
    subject: str | None = None
    priority: str | None = None
    assigned_agent_id: int | None = None
    assigned_user_id: int | None = None


class ConversationOut(ConversationBase):
    id: int
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
