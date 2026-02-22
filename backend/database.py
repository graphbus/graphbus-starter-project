"""SQLAlchemy database setup and ORM models."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./graphbus.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Application user."""

    __tablename__ = "users"

    id: str = Column(String, primary_key=True, default=_uuid)
    email: str = Column(String, unique=True, nullable=False, index=True)
    password_hash: str = Column(String, nullable=False)
    name: str = Column(String, nullable=False)
    created_at: datetime = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")


class Task(Base):
    """A to-do item owned by a user."""

    __tablename__ = "tasks"

    id: str = Column(String, primary_key=True, default=_uuid)
    title: str = Column(String, nullable=False)
    done: bool = Column(Boolean, default=False, nullable=False)
    user_id: str = Column(String, ForeignKey("users.id"), nullable=False)
    created_at: datetime = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner = relationship("User", back_populates="tasks")


def init_db() -> None:
    """Create all tables (idempotent)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:  # type: ignore[misc]
    """FastAPI dependency — yields a DB session then closes it."""
    db = SessionLocal()
    try:
        yield db  # type: ignore[misc]
    finally:
        db.close()
