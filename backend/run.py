"""GraphBus runtime bootstrap.

Creates the MessageBus, instantiates all agents, and wires
@subscribe-decorated methods to the bus. Imported by main.py so
the agents are ready before the first request arrives.
"""

from __future__ import annotations

import inspect
import logging

from graphbus_core_mock import MessageBus

logger = logging.getLogger(__name__)

# ---------- bus ----------

bus = MessageBus()

# ---------- agents ----------

from agents.auth_agent import AuthAgent, UserRegistrationAgent
from agents.notification_agent import NotificationAgent
from agents.task_agent import TaskManagerAgent

registration_agent = UserRegistrationAgent(bus=bus)
auth_agent = AuthAgent(bus=bus)
task_agent = TaskManagerAgent(bus=bus)
notification_agent = NotificationAgent(bus=bus)

# ---------- auto-wire subscriptions ----------

_agents = [registration_agent, auth_agent, task_agent, notification_agent]


def _wire_subscriptions() -> None:
    """Inspect every agent for @subscribe-decorated methods and register them."""
    for agent in _agents:
        for name, method in inspect.getmembers(agent, predicate=inspect.ismethod):
            topic = getattr(method, "_graphbus_subscribe_topic", None)
            if topic is not None:
                bus.subscribe(
                    topic,
                    method,
                    subscriber_name=f"{agent.__class__.__name__}.{name}",
                )
                logger.info(
                    "Wired %s.%s → %s",
                    agent.__class__.__name__,
                    name,
                    topic,
                )


_wire_subscriptions()
