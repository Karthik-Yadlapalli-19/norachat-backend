from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlmodel import Session
from app.routers import auth, health, chats
from app.core.database import get_session

app = FastAPI(title="NoraChat API")
app.include_router(auth.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(chats.router, prefix="/api")