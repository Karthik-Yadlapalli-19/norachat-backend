from datetime import timedelta
import uuid

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.security import create_access_token, generate_refresh_token, hash_value
from app.models import RefreshToken, User
from app.models.base import utcnow
from app.schemas.auth import TokenPair, TokenResponse, UserOut
from app.services import otp_service


def _issue_refresh_token(session: Session, user_id: uuid.UUID) -> str:
    """Create a refresh token, store its hash, return the plain token. No commit."""
    token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_value(token),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
    )
    return token


def login_with_otp(session: Session, email: str, code: str) -> TokenResponse:
    email = email.strip().lower()

    otp_service.verify_otp(session, email, code)

    user = session.exec(select(User).where(User.email == email)).first()
    is_new_user = user is None
    if is_new_user:
        user = User(email=email)
        session.add(user)
        session.flush()

    refresh_token = _issue_refresh_token(session, user.id)

    session.commit()
    session.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=refresh_token,
        is_new_user=is_new_user,
        user=UserOut.model_validate(user),
    )


def refresh_session(session: Session, refresh_token: str) -> TokenPair:
    now = utcnow()
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Session expired. Please log in again."
    )

    row = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == hash_value(refresh_token))
    ).first()

    if row is None:
        raise unauthorized

    user_id = row.user_id

    # Reuse detection: a revoked token was used again → assume theft
    if row.revoked_at is not None:
        session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, col(RefreshToken.revoked_at).is_(None))
            .values(revoked_at=now)
        )
        session.commit()
        raise unauthorized

    if row.expires_at < now:
        raise unauthorized

    # Rotate: revoke the old one, issue a new one
    row.revoked_at = now
    new_refresh_token = _issue_refresh_token(session, user_id)
    session.commit()

    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=new_refresh_token,
    )


def logout(session: Session, refresh_token: str) -> None:
    row = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == hash_value(refresh_token))
    ).first()

    if row and row.revoked_at is None:
        row.revoked_at = utcnow()
        session.commit()