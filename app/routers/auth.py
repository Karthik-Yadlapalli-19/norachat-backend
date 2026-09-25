from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.deps import get_current_user
from app.models import User
from app.models.base import utcnow
from app.schemas.auth import (
    MessageResponse,
    OtpRequest,
    OtpVerify,
    TokenResponse,
    UserOut,
    UserUpdate,
    TokenPair,
    RefreshRequest,
)
from app.services import auth_service, email_service, otp_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/request", response_model=MessageResponse)
def request_otp(body: OtpRequest, session: Session = Depends(get_session)):
    code = otp_service.create_otp(session, body.email)

    try:
        email_service.send_otp_email(body.email, code)
    except Exception as e:
        print(f"❌ Email failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't send the verification email. Please try again.",
        )

    return MessageResponse(message="Verification code sent to your email.")


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(body: OtpVerify, session: Session = Depends(get_session)):
    return auth_service.login_with_otp(session, body.email, body.code)

@router.get("/me", response_model=UserOut)
def get_me(
    user: User = Depends(get_current_user),
):
    return user

@router.patch("/me", response_model=UserOut)
def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user.name = body.name.strip()
    user.updated_at = utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, session: Session = Depends(get_session)):
    return auth_service.refresh_session(session, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, session: Session = Depends(get_session)):
    auth_service.logout(session, body.refresh_token)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    session.delete(user)
    session.commit()