"""FastAPI application — routes delegate to GraphBus agents."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import User, get_db, init_db
from run import auth_agent, notification_agent, registration_agent, task_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- lifespan ----------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialise the database on startup."""
    init_db()
    logger.info("Database initialised — tables created.")
    yield


app = FastAPI(
    title="GraphBus Starter Project",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
import os

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- request / response schemas ----------


class RegisterRequest(BaseModel):
    """Body for POST /api/auth/register."""
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    """Body for POST /api/auth/login."""
    email: str
    password: str


class TaskCreateRequest(BaseModel):
    """Body for POST /api/tasks."""
    title: str


class TaskUpdateRequest(BaseModel):
    """Body for PUT /api/tasks/{task_id}."""
    title: str | None = None
    done: bool | None = None


# ---------- health ----------


@app.get("/api/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


# ---------- auth routes ----------


@app.post("/api/auth/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    """Register a new user via UserRegistrationAgent."""
    result = registration_agent.register(db, body.email, body.password, body.name)

    # Flush any side-effects (welcome task)
    task_agent.flush_welcome_tasks(db)

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["reason"])
    return result


@app.post("/api/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """Authenticate via AuthAgent and return a JWT."""
    result = auth_agent.login(db, body.email, body.password)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result["reason"])
    return result


@app.get("/api/auth/me")
def me(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """Return the current user's profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"id": user.id, "email": user.email, "name": user.name}


# ---------- task routes ----------


@app.get("/api/tasks")
def list_tasks(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all tasks for the current user."""
    return task_agent.list_tasks(db, user_id)


@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """Create a task via TaskManagerAgent."""
    return task_agent.create_task(db, body.title, user_id)


@app.put("/api/tasks/{task_id}")
def update_task(
    task_id: str,
    body: TaskUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """Update a task via TaskManagerAgent."""
    result = task_agent.update_task(db, task_id, user_id, title=body.title, done=body.done)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result


@app.delete("/api/tasks/{task_id}")
def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a task via TaskManagerAgent."""
    deleted = task_agent.delete_task(db, task_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"deleted": True}
