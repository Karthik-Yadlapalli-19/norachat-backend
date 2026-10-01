
from fastapi.responses import StreamingResponse
from datetime import datetime
from fastapi import APIRouter, Depends, status, Query, UploadFile, File
from sqlmodel import Session

from app.core.database import get_session
from app.deps import get_current_user, get_owned_chat
from app.models import Chat, User
from app.schemas.chat import ChatCreate, ChatOut, ChatUpdate, MessagePage, MessageOut, SendMessageRequest
from app.schemas.attachment import AttachmentOut
from app.services import chat_service, message_service
from app.services import attachment_service, chat_service, message_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatOut])
def list_chats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return chat_service.list_chats(session, user.id)


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(
    body: ChatCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return chat_service.create_chat(session, user.id, body.title)


@router.get("/{chat_id}", response_model=ChatOut)
def get_chat(chat: Chat = Depends(get_owned_chat)):
    return chat


@router.patch("/{chat_id}", response_model=ChatOut)
def update_chat(
    body: ChatUpdate,
    chat: Chat = Depends(get_owned_chat),
    session: Session = Depends(get_session),
):
    return chat_service.update_chat(session, chat, body)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat: Chat = Depends(get_owned_chat),
    session: Session = Depends(get_session),
):
    chat_service.delete_chat(session, chat)

@router.get("/{chat_id}/messages", response_model=MessagePage)
def list_messages(
    limit: int = Query(default=50, ge=1, le=100),
    before: datetime | None = None,
    chat: Chat = Depends(get_owned_chat),
    session: Session = Depends(get_session),
):
    return message_service.list_messages(session, chat.id, limit, before)


@router.post("/{chat_id}/messages")
def send_message(
    body: SendMessageRequest,
    chat: Chat = Depends(get_owned_chat),
    session: Session = Depends(get_session),
):
    message_service.save_user_message(session, chat, body.content, body.id, body.attachment_ids)
    history, has_images = message_service.get_history(session, chat.id)

    model = settings.ollama_model
    if has_images and settings.ollama_vision_model:
        model = settings.ollama_vision_model

    return StreamingResponse(
        message_service.stream_reply(chat.id, history, model),
        media_type="application/x-ndjson",
    )

@router.post(
    "/{chat_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    file: UploadFile = File(...),
    chat: Chat = Depends(get_owned_chat),
    session: Session = Depends(get_session),
):
    attachment = attachment_service.create_attachment(session, chat, file)
    return attachment_service.to_out(attachment)