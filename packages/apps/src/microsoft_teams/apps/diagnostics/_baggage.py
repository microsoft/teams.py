"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from types import TracebackType
from typing import Any, Iterable, Literal, Mapping, Protocol, Self

from microsoft_teams.api import ActivityBase
from opentelemetry import baggage
from opentelemetry import context as otel_context

from ._constants import AGENT365_BAGGAGE_KEYS


class _ActivityContextSource(Protocol):
    activity: ActivityBase


_BaggageValue = str | int | None
_BaggageSource = ActivityBase | _ActivityContextSource | None
Agent365BaggageInclude = Literal[
    "sender_name",
    "agent_name",
    "agent_description",
    "sender_email",
    "agent_email",
]


class Agent365Baggage:
    """Opt-in Agent365 OpenTelemetry baggage bridge for Teams activity context."""

    def __init__(self, values: Mapping[str, _BaggageValue] | None = None):
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
        operation_source: str | None = None,
        channel_link: str | None = None,
        values: Mapping[str, _BaggageValue] | None = None,
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
            bridge.set(AGENT365_BAGGAGE_KEYS.agent_id, activity.recipient.agentic_app_id or activity.recipient.id)
            bridge.set(AGENT365_BAGGAGE_KEYS.agentic_user_id, activity.recipient.agentic_user_id)
            bridge.set(AGENT365_BAGGAGE_KEYS.agent_blueprint_id, activity.recipient.agentic_app_blueprint_id)
            bridge.set(AGENT365_BAGGAGE_KEYS.user_id, activity.from_.aad_object_id or activity.from_.id)

            if "sender_name" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.user_name, activity.from_.name)
            if "sender_email" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.user_email, activity.from_.email)
            if "agent_name" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.agent_name, activity.recipient.name)
            if "agent_email" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.agentic_user_email, activity.recipient.email)
            if "agent_description" in included:
                bridge.set(AGENT365_BAGGAGE_KEYS.agent_description, activity.recipient.user_role)

        bridge.operation_source(operation_source)
        bridge.set(AGENT365_BAGGAGE_KEYS.channel_link, channel_link)

        if values:
            for key, value in values.items():
                bridge.set(key, value)

        return bridge

    def set(self, key: str, value: _BaggageValue) -> Self:
        if value is None:
            return self

        normalized = str(value).strip()
        if not normalized:
            return self

        self._values[key] = normalized
        return self

    def operation_source(self, value: str | None) -> Self:
        return self.set(AGENT365_BAGGAGE_KEYS.operation_source, value)

    def __enter__(self) -> Self:
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
    operation_source: str | None = None,
    channel_link: str | None = None,
    values: Mapping[str, _BaggageValue] | None = None,
) -> Agent365Baggage:
    return Agent365Baggage.from_activity(
        source,
        include=include,
        operation_source=operation_source,
        channel_link=channel_link,
        values=values,
    )


def _activity_from_source(source: _BaggageSource) -> ActivityBase | None:
    if source is None:
        return None

    if isinstance(source, ActivityBase):
        return source

    return source.activity
