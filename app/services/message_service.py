import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

import httpx
from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.database import engine
from app.models import Chat, Message, MessageRole
from app.models.base import utcnow
from app.schemas.chat import MessageOut, MessagePage
from app.services import ollama_service

from collections import defaultdict

from app.models import Attachment
from app.services import attachment_service, storage_service

HISTORY_LIMIT = 20


def list_messages(
    session: Session,
    chat_id: uuid.UUID,
    limit: int,
    before: datetime | None,
) -> MessagePage:
    query = select(Message).where(Message.chat_id == chat_id)
    if before is not None:
        query = query.where(Message.created_at < before)

    rows = session.exec(
        query.order_by(col(Message.created_at).desc()).limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    rows = list(reversed(rows[:limit]))

    # 1 query: every attachment on this page
    attachments = session.exec(
        select(Attachment).where(col(Attachment.message_id).in_([m.id for m in rows]))
    ).all() if rows else []

    # 1 network call: sign every URL at once
    urls = storage_service.signed_urls([a.storage_key for a in attachments])

    by_message: dict[uuid.UUID, list] = defaultdict(list)
    for a in attachments:
        by_message[a.message_id].append(attachment_service.to_out(a, urls.get(a.storage_key)))

    return MessagePage(
        messages=[
            MessageOut.model_validate(m).model_copy(update={"attachments": by_message[m.id]})
            for m in rows
        ],
        has_more=has_more,
    )


def _touch_chat(chat: Chat, first_user_message: str | None = None) -> None:
    """Bump activity time; auto-title a brand-new chat from its first message."""
    chat.updated_at = utcnow()
    if first_user_message and chat.title == "New chat":
        title = first_user_message.strip().replace("\n", " ")
        chat.title = title[:40] + ("…" if len(title) > 40 else "")


def save_user_message(
    session: Session,
    chat: Chat,
    content: str,
    message_id: uuid.UUID | None,
    attachment_ids: list[uuid.UUID],
) -> Message:
    if message_id and session.get(Message, message_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Message already exists.")

    message = Message(chat_id=chat.id, role=MessageRole.user, content=content.strip())
    if message_id:
        message.id = message_id
    session.add(message)
    session.flush()                     # INSERT now, so attachments can reference it

    if attachment_ids:
        unique_ids = set(attachment_ids)
        attachments = session.exec(
            select(Attachment).where(
                col(Attachment.id).in_(unique_ids),
                Attachment.chat_id == chat.id,
                col(Attachment.message_id).is_(None),
            )
        ).all()
        if len(attachments) != len(unique_ids):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more attachments are invalid or already used.")
        for attachment in attachments:
            attachment.message_id = message.id
            session.add(attachment)

    _touch_chat(chat, first_user_message=content)
    session.add(chat)
    session.commit()
    session.refresh(message)
    return message


def get_history(session: Session, chat_id: uuid.UUID) -> tuple[list[dict], bool]:
    """Returns (Ollama messages oldest → newest, whether any images are included)."""
    rows = list(reversed(session.exec(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(col(Message.created_at).desc())
        .limit(HISTORY_LIMIT)
    ).all()))

    # One query for all attachments in the window, not one query per message
    attachments_by_message: dict[uuid.UUID, list[Attachment]] = defaultdict(list)
    if rows:
        for a in session.exec(
            select(Attachment).where(col(Attachment.message_id).in_([m.id for m in rows]))
        ).all():
            attachments_by_message[a.message_id].append(a)

    latest_user_id = next((m.id for m in reversed(rows) if m.role == MessageRole.user), None)

    history: list[dict] = []
    has_images = False
    for m in rows:
        content = m.content
        images: list[str] = []

        for a in attachments_by_message[m.id]:
            if a.extracted_text is not None:                       # document
                content = f'<document name="{a.filename}">\n{a.extracted_text}\n</document>\n\n{content}'
            elif m.id == latest_user_id:                           # image in the newest message
                images.append(attachment_service.image_for_model(storage_service.read(a.storage_key)))
            else:                                                  # older image: just a note
                content = f"[Earlier image: {a.filename}]\n{content}"

        entry = {"role": m.role.value, "content": content}
        if images:
            entry["images"] = images
            has_images = True
        history.append(entry)

    return history, has_images


def _event(type_: str, **data) -> str:
    return json.dumps({"type": type_, **data}) + "\n"


async def stream_reply(chat_id: uuid.UUID, history: list[dict], model: str) -> AsyncIterator[str]:
    reply = ""
    eval_count = None

    try:
        async for chunk in ollama_service.stream_chat(history, model):
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                reply += delta
                yield _event("delta", content=delta)
            if chunk.get("done"):
                eval_count = chunk.get("eval_count")
    except httpx.HTTPError as e:
        print(f"❌ Ollama error: {e}")
        yield _event("error", detail="Nora is unavailable right now. Please try again.")
        return

    # Save the finished reply with a fresh session (see note below)
    with Session(engine) as session:
        message = Message(
            chat_id=chat_id,
            role=MessageRole.assistant,
            content=reply,
            model=settings.ollama_model,
            eval_count=eval_count,
        )
        session.add(message)
        chat = session.get(Chat, chat_id)
        if chat:
            _touch_chat(chat)
            session.add(chat)
        session.commit()
        session.refresh(message)

        yield _event("done", message=MessageOut.model_validate(message).model_dump(mode="json"))