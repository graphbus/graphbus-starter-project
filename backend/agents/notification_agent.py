"""Notification agent — reacts to domain events and dispatches alerts.

In this starter project notifications are logged to stdout.
A production implementation would integrate email, Slack, or push.
"""

from __future__ import annotations

import logging
from typing import Any

from graphbus_core import GraphBusNode, subscribe
from graphbus_core.runtime.message_bus import MessageBus

logger = logging.getLogger(__name__)


class NotificationAgent(GraphBusNode):
    """Listens for domain events and dispatches user-facing notifications.

    Currently logs to stdout; swap in your preferred transport for production.

    **Build-mode guidance** — an LLM may propose:
    * Email integration (SMTP / SendGrid / SES).
    * Slack webhook notifications.
    * In-app notification centre with read/unread state.
    * Notification preferences per user.
    """

    SYSTEM_PROMPT = (
        "You are the NotificationAgent. "
        "You listen for domain events and dispatch notifications. "
        "In Build Mode propose: email integration, Slack webhooks, "
        "in-app notification centre, per-user preferences."
    )

    def __init__(self, bus: MessageBus | None = None, memory: Any = None) -> None:
        super().__init__(bus=bus, memory=memory)

    @subscribe("/Auth/UserRegistered")
    def on_user_registered(self, payload: dict) -> None:
        """Send a welcome notification when a new user registers."""
        logger.info(
            "NOTIFICATION: Welcome %s (%s)! Your account has been created.",
            payload.get("name"),
            payload.get("email"),
        )

    @subscribe("/Auth/LoginSucceeded")
    def on_login_succeeded(self, payload: dict) -> None:
        """Log a notification when a user logs in."""
        logger.info(
            "NOTIFICATION: User %s logged in successfully.",
            payload.get("email"),
        )

    @subscribe("/Tasks/Created")
    def on_task_created(self, payload: dict) -> None:
        """Log a notification when a task is created."""
        logger.info(
            "NOTIFICATION: Task '%s' created for user %s.",
            payload.get("title"),
            payload.get("user_id"),
        )

    @subscribe("/Tasks/Deleted")
    def on_task_deleted(self, payload: dict) -> None:
        """Log a notification when a task is deleted."""
        logger.info(
            "NOTIFICATION: Task %s deleted by user %s.",
            payload.get("task_id"),
            payload.get("user_id"),
        )
