"""Authentication agents — registration and login.

These agents own the ``/Auth/*`` topic namespace on the message bus.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any

from sqlalchemy.orm import Session

from graphbus_core_mock import GraphBusNode, MessageBus, depends_on, schema_method, subscribe


class UserRegistrationAgent(GraphBusNode):
    """Validates and registers new users.

    Publishes ``/Auth/UserRegistered`` on success so downstream agents
    (e.g. TaskManagerAgent) can react to new signups.

    **Build-mode guidance** — an LLM may propose:
    * Stronger password policies (min length, complexity).
    * Email-verification flow before activation.
    * Rate-limiting on the registration endpoint.
    Coordinate with ``AuthAgent`` before changing the
    ``/Auth/UserRegistered`` payload shape.
    """

    SYSTEM_PROMPT = (
        "You are the UserRegistrationAgent. "
        "You validate and register new users, publishing /Auth/UserRegistered on success. "
        "In Build Mode you can propose: stronger password policies, email verification flows. "
        "Coordinate with AuthAgent before changing the /Auth/UserRegistered payload."
    )

    def __init__(self, bus: MessageBus | None = None, memory: Any = None) -> None:
        super().__init__(bus=bus, memory=memory)

    @schema_method(
        input_schema={"email": str, "password": str, "name": str},
        output_schema={"success": bool, "user_id": str, "reason": str},
    )
    def register(self, db: Session, email: str, password: str, name: str) -> dict:
        """Register a new user account.

        Returns a dict with ``success``, ``user_id``, and ``reason``.
        """
        from database import User

        # Validate inputs
        if not email or "@" not in email:
            return {"success": False, "user_id": "", "reason": "Invalid email address"}
        if len(password) < 8:
            return {"success": False, "user_id": "", "reason": "Password must be at least 8 characters"}
        if not name.strip():
            return {"success": False, "user_id": "", "reason": "Name is required"}

        # Check uniqueness
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return {"success": False, "user_id": "", "reason": "Email already registered"}

        # Hash password
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256(f"{salt}${password}".encode()).hexdigest()
        password_hash = f"{salt}${password_hash}"

        user_id = str(uuid.uuid4())
        user = User(id=user_id, email=email, password_hash=password_hash, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Publish domain event
        self.publish("/Auth/UserRegistered", {"user_id": user_id, "email": email, "name": name})

        return {"success": True, "user_id": user_id, "reason": ""}


class AuthAgent(GraphBusNode):
    """Handles user login and JWT issuance.

    Publishes ``/Auth/LoginSucceeded`` on successful authentication.

    **Build-mode guidance** — an LLM may propose:
    * Refresh-token rotation.
    * Account lockout after N failed attempts.
    * Multi-factor authentication.
    """

    SYSTEM_PROMPT = (
        "You are the AuthAgent. "
        "You authenticate users and issue JWT tokens, publishing /Auth/LoginSucceeded on success. "
        "In Build Mode you can propose: refresh-token rotation, account lockout, MFA. "
        "Depends on UserRegistrationAgent for user records."
    )

    _graphbus_depends_on = ["UserRegistrationAgent"]

    def __init__(self, bus: MessageBus | None = None, memory: Any = None) -> None:
        super().__init__(bus=bus, memory=memory)

    @schema_method(
        input_schema={"email": str, "password": str},
        output_schema={"success": bool, "token": str, "reason": str},
    )
    def login(self, db: Session, email: str, password: str) -> dict:
        """Authenticate a user and return a JWT.

        Returns a dict with ``success``, ``token``, and ``reason``.
        """
        from auth import create_access_token
        from database import User

        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"success": False, "token": "", "reason": "Invalid credentials"}

        # Verify password
        stored = user.password_hash
        salt, expected_hash = stored.split("$", 1)
        candidate_hash = hashlib.sha256(f"{salt}${password}".encode()).hexdigest()
        if candidate_hash != expected_hash:
            return {"success": False, "token": "", "reason": "Invalid credentials"}

        token = create_access_token({"sub": user.id, "email": user.email})

        self.publish("/Auth/LoginSucceeded", {"user_id": user.id, "email": user.email})

        return {"success": True, "token": token, "reason": ""}
