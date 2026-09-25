from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def created_at_field():
    """TIMESTAMPTZ NOT NULL DEFAULT now()"""
    return Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


def optional_datetime_field():
    """TIMESTAMPTZ (nullable)"""
    return Field(default=None, sa_type=DateTime(timezone=True))