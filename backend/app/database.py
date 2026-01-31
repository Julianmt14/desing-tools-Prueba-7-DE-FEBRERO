from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", settings.sqlalchemy_database_uri)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos de la aplicación."""


engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    """Genera una sesión de base de datos para inyección en FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
