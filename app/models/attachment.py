import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Text
from sqlmodel import Field, SQLModel

from app.models.base import created_at_field


class Attachment(SQLModel, table=True):
    __tablename__ = "attachments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    chat_id: uuid.UUID = Field(foreign_key="chats.id", ondelete="CASCADE")
    message_id: uuid.UUID | None = Field(
        default=None, foreign_key="messages.id", ondelete="CASCADE"
    )
    filename: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    size_bytes: int = Field(sa_type=BigInteger)
    storage_key: str = Field(max_length=500)
    extracted_text: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = created_at_field()