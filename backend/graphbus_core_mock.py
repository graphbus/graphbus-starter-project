"""
GraphBus Core — lightweight runtime mock.

Drop this file into any project to use GraphBus agent patterns
without a pip dependency. Production projects use `pip install graphbus`.
"""

from __future__ import annotations

import functools
from typing import Any, Callable


class MessageBus:
    """In-process publish/subscribe message bus.

    Agents publish domain events to named topics; other agents
    subscribe to react. In production the real graphbus-core swaps
    this for a distributed transport — the API stays identical.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[str, Callable]]] = {}

    def subscribe(
        self,
        topic: str,
        handler: Callable,
        *,
        subscriber_name: str = "",
    ) -> None:
        """Register *handler* to be called when *topic* is published."""
        self._subscribers.setdefault(topic, []).append(
            (subscriber_name, handler),
        )

    def publish(self, topic: str, payload: Any) -> None:
        """Deliver *payload* to every handler subscribed to *topic*."""
        for _, handler in self._subscribers.get(topic, []):
            handler(payload)


class GraphBusNode:
    """Base class for all GraphBus agents.

    Subclasses declare a ``SYSTEM_PROMPT`` that the LLM build-mode
    reads to understand each agent's role and negotiate changes.
    """

    SYSTEM_PROMPT: str = ""

    def __init__(
        self,
        bus: MessageBus | None = None,
        memory: Any = None,
    ) -> None:
        self._bus = bus
        self._memory = memory

    def publish(self, topic: str, payload: Any) -> None:
        """Publish a domain event onto the message bus."""
        if self._bus:
            self._bus.publish(topic, payload)


# --------------- decorators ---------------


def subscribe(topic: str) -> Callable:
    """Mark a method as a subscriber to *topic*.

    ``run.py`` introspects this attribute when wiring agents to the bus.
    """

    def decorator(fn: Callable) -> Callable:
        fn._graphbus_subscribe_topic = topic  # type: ignore[attr-defined]
        return fn

    return decorator


def schema_method(
    input_schema: dict,
    output_schema: dict,
) -> Callable:
    """Attach input/output schema metadata to an agent method.

    Used by build-mode to validate cross-agent contracts.
    """

    def decorator(fn: Callable) -> Callable:
        fn._graphbus_input_schema = input_schema  # type: ignore[attr-defined]
        fn._graphbus_output_schema = output_schema  # type: ignore[attr-defined]
        return fn

    return decorator


def depends_on(*agent_names: str) -> Callable:
    """Declare that the decorated agent/method depends on other agents.

    Build-mode uses this to determine negotiation order.
    """

    def decorator(cls: Any) -> Any:
        cls._graphbus_depends_on = list(agent_names)
        return cls

    return decorator
