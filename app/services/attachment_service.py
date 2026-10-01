import io

import pymupdf
from docx import Document
from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session

from app.models import Attachment, Chat
from app.schemas.attachment import AttachmentOut
from app.services import storage_service
import base64

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()
MAX_IMAGE_SIDE = 1536

MAX_BYTES = 20 * 1024 * 1024          # 20 MB, same as the bucket limit
MAX_TEXT_CHARS = 60_000               # ~15-20 pages; larger needs RAG later

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ---------- Type detection ----------

def detect_type(data: bytes, filename: str) -> tuple[str, str]:
    """Identify the file by its actual bytes, not its name. Returns (mime, extension)."""
    name = filename.lower()

    if data.startswith(b"%PDF"):
        return "application/pdf", ".pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"mif1", b"msf1"):
        return "image/heic", ".heic"
    if data.startswith(b"PK\x03\x04") and name.endswith(".docx"):
        return DOCX_MIME, ".docx"
    if name.endswith((".txt", ".md")):
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return ("text/markdown", ".md") if name.endswith(".md") else ("text/plain", ".txt")

    raise HTTPException(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "Unsupported file type. Allowed: PDF, DOCX, TXT, MD, JPG, PNG, WEBP, HEIC.",
    )


# ---------- Text extraction ----------

def extract_text(data: bytes, mime: str) -> str | None:
    try:
        if mime == "application/pdf":
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                pages = [f"[Page {i + 1}]\n{page.get_text()}" for i, page in enumerate(doc)]
            text = "\n\n".join(pages)
        elif mime == DOCX_MIME:
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif mime.startswith("text/"):
            text = data.decode("utf-8")
        else:
            return None                          # images: no text extraction
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Couldn't read this file. It may be corrupted.")

    text = text.replace("\x00", "").strip()     # Postgres TEXT can't store NUL bytes

    if mime == "application/pdf" and len(text.replace("[Page", "")) < 20:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This PDF looks scanned (no text layer). Scanned PDFs aren't supported yet.",
        )
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This document is too long for now. Try one under ~15 pages.",
        )
    return text


# ---------- Create ----------

def create_attachment(session: Session, chat: Chat, upload: UploadFile) -> Attachment:
    data = upload.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is larger than 20 MB.")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "File is empty.")

    filename = upload.filename or "file"
    mime, ext = detect_type(data, filename)
    text = extract_text(data, mime)

    attachment = Attachment(
        user_id=chat.user_id,
        chat_id=chat.id,
        filename=filename[:255],
        mime_type=mime,
        size_bytes=len(data),
        storage_key="",
        extracted_text=text,
    )
    attachment.storage_key = f"{chat.user_id}/{chat.id}/{attachment.id}{ext}"

    storage_service.save(attachment.storage_key, data, mime)

    try:
        session.add(attachment)
        session.commit()
        session.refresh(attachment)
    except Exception:
        session.rollback()
        storage_service.delete([attachment.storage_key])   # don't leave an orphan file
        raise

    return attachment


def to_out(attachment: Attachment) -> AttachmentOut:
    return AttachmentOut(
        id=attachment.id,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        url=storage_service.signed_url(attachment.storage_key),
        has_text=attachment.extracted_text is not None,
        created_at=attachment.created_at,
    )

def image_for_model(data: bytes) -> str:
    """Any supported image → resized JPEG → base64 string for Ollama."""
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image)       # apply the iPhone's rotation
    image = image.convert("RGB")
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode()

def to_out(attachment: Attachment, url: str | None = None) -> AttachmentOut:
    return AttachmentOut(
        id=attachment.id,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        url=url or storage_service.signed_url(attachment.storage_key),
        has_text=attachment.extracted_text is not None,
        created_at=attachment.created_at,
    )