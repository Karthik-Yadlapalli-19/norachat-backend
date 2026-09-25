from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlmodel import Session, col, select

from app.core.security import generate_otp, hash_value,  verify_hash
from app.models import EmailOtp
from app.models.base import utcnow

OTP_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60


def create_otp(session: Session, email: str) -> str:
    email = email.strip().lower()
    now = utcnow()

    # 1. Cooldown: block requesting a new code too quickly
    latest = session.exec(
        select(EmailOtp)
        .where(EmailOtp.email == email)
        .order_by(col(EmailOtp.created_at).desc())
    ).first()

    if latest and now - latest.created_at < timedelta(seconds=RESEND_COOLDOWN_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait a minute before requesting a new code.",
        )

    # 2. Invalidate older unused codes, so only the newest one works
    session.execute(
        update(EmailOtp)
        .where(EmailOtp.email == email, col(EmailOtp.consumed_at).is_(None))
        .values(consumed_at=now)
    )

    # 3. Create and store the new code (hashed)
    code = generate_otp()
    session.add(
        EmailOtp(
            email=email,
            code_hash=hash_value(code),
            expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        )
    )
    session.commit()

    return code   # plain code goes to the email, never to the DB

MAX_ATTEMPTS = 5

def verify_otp(session: Session, email: str, code: str) -> None:
    """Raises HTTPException if the code is wrong. Marks it used if correct (no commit)."""
    now = utcnow()

    otp = session.exec(
        select(EmailOtp)
        .where(EmailOtp.email == email, col(EmailOtp.consumed_at).is_(None))
        .order_by(col(EmailOtp.created_at).desc())
    ).first()

    if otp is None or otp.expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code expired or invalid. Please request a new one.")

    if otp.attempts >= MAX_ATTEMPTS:
        otp.consumed_at = now
        session.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many attempts. Please request a new code.")

    if not verify_hash(code, otp.code_hash):
        otp.attempts += 1
        session.commit()               # save the attempt BEFORE raising
        remaining = MAX_ATTEMPTS - otp.attempts
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Incorrect code. {remaining} attempts left.")

    otp.consumed_at = now              # correct: single-use from now on