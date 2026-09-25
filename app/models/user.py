import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import created_at_field


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=255, unique=True)
    name: str | None = Field(default=None, max_length=100)
    created_at: datetime = created_at_field()
    updated_at: datetime = created_at_field()