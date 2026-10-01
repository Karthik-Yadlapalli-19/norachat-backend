import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from app.models import MessageRole
from app.schemas.attachment import AttachmentOut

class ChatCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class ChatUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    pinned: bool | None = None


class ChatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    pinned_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chat_id: uuid.UUID
    role: MessageRole
    content: str
    model: str | None
    created_at: datetime
    attachments: list[AttachmentOut] = []


class MessagePage(BaseModel):
    messages: list[MessageOut]      # oldest → newest, ready to display
    has_more: bool                  # are there older messages to load?

class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    id: uuid.UUID | None = None
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=5)