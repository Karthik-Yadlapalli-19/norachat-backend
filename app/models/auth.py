import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.base import created_at_field, optional_datetime_field


class EmailOtp(SQLModel, table=True):
    __tablename__ = "email_otps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=255)
    code_hash: str = Field(max_length=255)
    attempts: int = 0
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    consumed_at: datetime | None = optional_datetime_field()
    created_at: datetime = created_at_field()


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    token_hash: str = Field(max_length=255, unique=True)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    revoked_at: datetime | None = optional_datetime_field()
    created_at: datetime = created_at_field()