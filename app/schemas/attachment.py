import uuid
from datetime import datetime

from pydantic import BaseModel


class AttachmentOut(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    url: str            # signed URL, valid for 1 hour
    has_text: bool      # True for documents, False for images
    created_at: datetime