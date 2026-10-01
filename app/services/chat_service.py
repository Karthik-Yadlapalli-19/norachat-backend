import uuid

from sqlmodel import Session, col, select

from app.models import Chat
from app.models.base import utcnow
from app.schemas.chat import ChatUpdate

from app.models import Attachment, Chat
from app.services import storage_service


def list_chats(session: Session, user_id: uuid.UUID) -> list[Chat]:
    return list(
        session.exec(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(
                col(Chat.pinned_at).desc().nulls_last(),   # pinned first, newest pin on top
                col(Chat.updated_at).desc(),               # then most recent activity
            )
        ).all()
    )


def create_chat(session: Session, user_id: uuid.UUID, title: str | None) -> Chat:
    chat = Chat(user_id=user_id, title=title.strip() if title else "New chat")
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def update_chat(session: Session, chat: Chat, data: ChatUpdate) -> Chat:
    changes = data.model_dump(exclude_unset=True)

    if "title" in changes and changes["title"] is not None:
        chat.title = changes["title"].strip()

    if "pinned" in changes and changes["pinned"] is not None:
        if changes["pinned"] and chat.pinned_at is None:
            chat.pinned_at = utcnow()           # pin (keep original time if already pinned)
        elif not changes["pinned"]:
            chat.pinned_at = None               # unpin

    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


def delete_chat(session: Session, chat: Chat) -> None:
    # 1. Collect file paths BEFORE the rows disappear
    keys = list(session.exec(
        select(Attachment.storage_key).where(Attachment.chat_id == chat.id)
    ).all())

    # 2. Delete the chat (cascade removes its messages + attachment rows)
    session.delete(chat)
    session.commit()

    # 3. Remove the files from Supabase
    storage_service.delete_quietly(keys)