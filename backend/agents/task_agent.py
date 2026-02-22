"""Task management agent — CRUD operations and lifecycle events.

Owns the ``/Tasks/*`` topic namespace on the message bus.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from graphbus_core import GraphBusNode, schema_method, subscribe
from graphbus_core.runtime.message_bus import MessageBus


class TaskManagerAgent(GraphBusNode):
    """Handles task CRUD and publishes lifecycle events.

    Subscribes to ``/Auth/UserRegistered`` to create a welcome task
    for every new user.

    **Build-mode guidance** — an LLM may propose:
    * Due-date enforcement and overdue notifications.
    * Priority queues (low / medium / high / critical).
    * Assignment notifications via NotificationAgent.
    """

    SYSTEM_PROMPT = (
        "You are the TaskManagerAgent. "
        "You handle task CRUD operations and publish lifecycle events. "
        "In Build Mode propose: due-date enforcement, priority queues, assignment notifications."
    )

    def __init__(self, bus: MessageBus | None = None, memory: Any = None) -> None:
        super().__init__(bus=bus, memory=memory)
        self._pending_welcome: list[dict] = []

    # ---- subscriptions ----

    @subscribe("/Auth/UserRegistered")
    def on_user_registered(self, payload: dict) -> None:
        """Create a default welcome task for newly registered users."""
        self._pending_welcome.append(payload)

    def flush_welcome_tasks(self, db: Session) -> None:
        """Persist any pending welcome tasks (called after bus events settle)."""
        from database import Task

        for p in self._pending_welcome:
            task = Task(
                id=str(uuid.uuid4()),
                title="Welcome! Start by exploring the dashboard.",
                done=False,
                user_id=p["user_id"],
            )
            db.add(task)
        if self._pending_welcome:
            db.commit()
        self._pending_welcome.clear()

    # ---- CRUD ----

    @schema_method(
        input_schema={"title": str, "user_id": str},
        output_schema={"task_id": str, "title": str},
    )
    def create_task(self, db: Session, title: str, user_id: str) -> dict:
        """Create a new task for the given user."""
        from database import Task

        task_id = str(uuid.uuid4())
        task = Task(id=task_id, title=title, done=False, user_id=user_id)
        db.add(task)
        db.commit()
        db.refresh(task)

        self.publish("/Tasks/Created", {"task_id": task_id, "title": title, "user_id": user_id})
        return {"task_id": task_id, "title": title}

    @schema_method(
        input_schema={"user_id": str},
        output_schema={"tasks": list},
    )
    def list_tasks(self, db: Session, user_id: str) -> list[dict]:
        """Return all tasks for a user."""
        from database import Task

        tasks = db.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.desc()).all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "done": t.done,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]

    @schema_method(
        input_schema={"task_id": str, "title": str, "done": bool},
        output_schema={"task_id": str, "title": str, "done": bool},
    )
    def update_task(
        self,
        db: Session,
        task_id: str,
        user_id: str,
        title: str | None = None,
        done: bool | None = None,
    ) -> dict | None:
        """Update an existing task. Returns ``None`` if not found."""
        from database import Task

        task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
        if not task:
            return None

        if title is not None:
            task.title = title
        if done is not None:
            task.done = done

        db.commit()
        db.refresh(task)

        self.publish("/Tasks/Updated", {"task_id": task_id, "title": task.title, "done": task.done})
        return {"task_id": task.id, "title": task.title, "done": task.done}

    @schema_method(
        input_schema={"task_id": str, "user_id": str},
        output_schema={"deleted": bool},
    )
    def delete_task(self, db: Session, task_id: str, user_id: str) -> bool:
        """Delete a task. Returns ``True`` if deleted, ``False`` if not found."""
        from database import Task

        task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
        if not task:
            return False

        db.delete(task)
        db.commit()

        self.publish("/Tasks/Deleted", {"task_id": task_id, "user_id": user_id})
        return True
