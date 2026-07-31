"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import math
from types import TracebackType
from typing import Any, Collection, Iterable, Literal, Mapping, Protocol, Self, TypedDict, TypeVar

from microsoft_teams.api import ActivityBase, AgenticUser
from opentelemetry import baggage
from opentelemetry import context as otel_context

from ._constants import AGENT365_BAGGAGE_KEYS, Agent365BaggageKeys


class _ActivityContextSource(Protocol):
    activity: ActivityBase


Agent365BaggageValue = str | int | float | None
Agent365BaggageEntries = Mapping[str, Agent365BaggageValue]
_BaggageSource = ActivityBase | _ActivityContextSource | None
Agent365BaggageInclude = Literal[
    "senderName",
    "agentName",
    "agentDescription",
    "senderEmail",
    "agentEmail",
]
_T = TypeVar("_T")


class Agent365BaggageOptions(TypedDict, total=False):
    """Host-wide options for Agent365 baggage derived from inbound activities."""

    include: Collection[Agent365BaggageInclude]
    operation_source: Agent365BaggageValue
    channel_link: Agent365BaggageValue
    additional_baggage: Agent365BaggageEntries


class Agent365ScopeOptions(Agent365BaggageOptions, total=False):
    """Host-wide defaults for proactive Agent365 baggage scopes."""

    service_url: Agent365BaggageValue
    agent_id: Agent365BaggageValue
    channel_name: Agent365BaggageValue


class Agent365ScopeOpener(Protocol):
    """Opens a proactive Agent365 baggage scope with bound host policy."""

    def __call__(
        self,
        *,
        agentic_user: AgenticUser | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        sender_name: str | None = None,
        sender_email: str | None = None,
        agent_name: str | None = None,
        agent_email: str | None = None,
        agent_description: str | None = None,
        additional_baggage: Agent365BaggageEntries | None = None,
    ) -> "Agent365Baggage": ...


class Agent365Baggage:
    """Opt-in Agent365 OpenTelemetry baggage bridge for Teams activity context."""

    def __init__(self, values: Agent365BaggageEntries | None = None):
        self._values: dict[str, str] = {}
        self._token: Any = None
        if values:
            for key, value in values.items():
                self.set(key, value)

    @classmethod
    def from_activity(
        cls,
        source: _BaggageSource,
        *,
        include: Iterable[Agent365BaggageInclude] | None = None,
        operation_source: Agent365BaggageValue = None,
        channel_link: Agent365BaggageValue = None,
        additional_baggage: Agent365BaggageEntries | None = None,
    ) -> Self:
        bridge = cls()
        activity = _activity_from_source(source)
        included = set(include or ())

        if activity is not None:
            tenant = activity.recipient.tenant_id or activity.conversation.tenant_id
            if tenant is None and activity.channel_data is not None and activity.channel_data.tenant is not None:
                tenant = activity.channel_data.tenant.id

            bridge.set(AGENT365_BAGGAGE_KEYS.tenant_id, tenant)
            bridge.set(AGENT365_BAGGAGE_KEYS.conversation_id, activity.conversation.id)
            bridge.set(AGENT365_BAGGAGE_KEYS.conversation_item_link, activity.service_url)
            bridge.set(AGENT365_BAGGAGE_KEYS.channel_name, activity.channel_id)
            bridge.set(
                AGENT365_BAGGAGE_KEYS.agent_id,
                activity.recipient.agentic_app_instance_id or activity.recipient.id,
            )
            bridge.set(AGENT365_BAGGAGE_KEYS.agentic_user_id, activity.recipient.agentic_user_id)
            bridge.set(AGENT365_BAGGAGE_KEYS.agent_blueprint_id, activity.recipient.agentic_blueprint_id)
            bridge.set(AGENT365_BAGGAGE_KEYS.user_id, activity.from_.aad_object_id or activity.from_.id)

            if "senderName" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.user_name, activity.from_.name)
            if "senderEmail" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.user_email, activity.from_.email)
            if "agentName" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.agent_name, activity.recipient.name)
            if "agentEmail" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.agentic_user_email, activity.recipient.email)
            if "agentDescription" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.agent_description, activity.recipient.user_role)

        bridge.operation_source(operation_source)
        bridge.set(AGENT365_BAGGAGE_KEYS.channel_link, channel_link)

        if additional_baggage:
            for key, value in additional_baggage.items():
                bridge.set(key, value)

        return bridge

    def set(self, key: str, value: Agent365BaggageValue) -> Self:
        if value is None:
            return self

        if isinstance(value, float) and not math.isfinite(value):
            return self

        key = key.strip()
        normalized = str(value).strip()
        if not key or not normalized:
            return self

        self._values[key] = normalized
        return self

    def operation_source(self, value: Agent365BaggageValue) -> Self:
        return self.set(AGENT365_BAGGAGE_KEYS.operation_source, value)

    def __enter__(self) -> Self:
        if not self._values:
            return self

        context = otel_context.get_current()
        for key, value in self._values.items():
            context = baggage.set_baggage(key, value, context=context)

        self._token = otel_context.attach(context)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._token is not None:
            otel_context.detach(self._token)
            self._token = None


def agent365_baggage(
    source: _BaggageSource = None,
    *,
    include: Iterable[Agent365BaggageInclude] | None = None,
    operation_source: Agent365BaggageValue = None,
    channel_link: Agent365BaggageValue = None,
    additional_baggage: Agent365BaggageEntries | None = None,
) -> Agent365Baggage:
    return Agent365Baggage.from_activity(
        source,
        include=include,
        operation_source=operation_source,
        channel_link=channel_link,
        additional_baggage=additional_baggage,
    )


def create_agent365_scope(options: Agent365ScopeOptions | Literal[False] | None = None) -> Agent365ScopeOpener:
    """Create a reusable proactive Agent365 baggage scope opener."""
    disabled = options is False
    bound: Agent365ScopeOptions
    if options is False or options is None:
        bound = {}
    else:
        bound = options
    included = set(bound.get("include", ()))

    def open_scope(
        *,
        agentic_user: AgenticUser | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        sender_name: str | None = None,
        sender_email: str | None = None,
        agent_name: str | None = None,
        agent_email: str | None = None,
        agent_description: str | None = None,
        additional_baggage: Agent365BaggageEntries | None = None,
    ) -> Agent365Baggage:
        if disabled:
            return Agent365Baggage()

        values: dict[str, Agent365BaggageValue] = {
            AGENT365_BAGGAGE_KEYS.tenant_id: agentic_user.tenant_id if agentic_user else None,
            AGENT365_BAGGAGE_KEYS.conversation_id: conversation_id,
            AGENT365_BAGGAGE_KEYS.conversation_item_link: bound.get("service_url"),
            AGENT365_BAGGAGE_KEYS.channel_name: bound.get("channel_name"),
            AGENT365_BAGGAGE_KEYS.channel_link: bound.get("channel_link"),
            AGENT365_BAGGAGE_KEYS.agent_id: (
                agentic_user.agentic_app_instance_id if agentic_user else bound.get("agent_id")
            ),
            AGENT365_BAGGAGE_KEYS.agentic_user_id: agentic_user.agentic_user_id if agentic_user else None,
            AGENT365_BAGGAGE_KEYS.agent_blueprint_id: agentic_user.agentic_blueprint_id if agentic_user else None,
            AGENT365_BAGGAGE_KEYS.user_id: user_id,
            AGENT365_BAGGAGE_KEYS.operation_source: bound.get("operation_source"),
        }
        optional_identity = {
            "senderName": (AGENT365_BAGGAGE_KEYS.user_name, sender_name),
            "senderEmail": (AGENT365_BAGGAGE_KEYS.user_email, sender_email),
            "agentName": (AGENT365_BAGGAGE_KEYS.agent_name, agent_name),
            "agentEmail": (AGENT365_BAGGAGE_KEYS.agentic_user_email, agent_email),
            "agentDescription": (AGENT365_BAGGAGE_KEYS.agent_description, agent_description),
        }
        for include in included:
            key, value = optional_identity[include]
            values[key] = value

        values.update(bound.get("additional_baggage", {}))
        if additional_baggage:
            values.update(additional_baggage)
        return Agent365Baggage(values)

    return open_scope


def _activity_from_source(source: _BaggageSource) -> ActivityBase | None:
    if source is None:
        return None

    if isinstance(source, ActivityBase):
        return source

    return source.activity


__all__ = [
    "Agent365Baggage",
    "Agent365BaggageEntries",
    "Agent365BaggageInclude",
    "Agent365BaggageKeys",
    "Agent365BaggageOptions",
    "Agent365BaggageValue",
    "Agent365ScopeOpener",
    "Agent365ScopeOptions",
    "agent365_baggage",
    "create_agent365_scope",
]
