from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/", tags=["health"])
def health():
    return {"status": "ok"}


@router.get("/db", tags=["health"])
def health_db(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"database": "connected"}