import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Text
from sqlmodel import Field, SQLModel

from app.models.base import created_at_field, optional_datetime_field


class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    title: str = Field(default="New chat", max_length=200)
    pinned_at: datetime | None = optional_datetime_field()
    created_at: datetime = created_at_field()
    updated_at: datetime = created_at_field()


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    chat_id: uuid.UUID = Field(foreign_key="chats.id", ondelete="CASCADE")
    role: MessageRole
    content: str = Field(sa_type=Text)
    model: str | None = Field(default=None, max_length=100)
    eval_count: int | None = None
    created_at: datetime = created_at_field()