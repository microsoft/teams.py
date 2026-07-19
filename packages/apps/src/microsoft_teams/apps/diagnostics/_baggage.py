"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from contextvars import Token
from types import TracebackType
from typing import TYPE_CHECKING, Self

from microsoft_teams.api import ActivityBase
from opentelemetry import baggage
from opentelemetry import context as otel_context
from opentelemetry.context import Context

from ._constants import APP_BAGGAGE_KEYS

if TYPE_CHECKING:
    from ..routing import ActivityContext


class _TeamsBaggageScope(AbstractContextManager[None]):
    def __init__(self, entries: dict[str, str]) -> None:
        self._entries = entries
        self._token: Token[Context] | None = None

    def __enter__(self) -> None:
        ctx = otel_context.get_current()
        for key, value in self._entries.items():
            ctx = baggage.set_baggage(key, value, context=ctx)
        self._token = otel_context.attach(ctx)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._token is not None:
            otel_context.detach(self._token)
            self._token = None


class TeamsBaggageBuilder:
    """Builds an OpenTelemetry baggage scope for Teams Agent365 context."""

    def __init__(self) -> None:
        self._entries: dict[str, str] = {}

    @classmethod
    def from_activity(cls, activity: ActivityBase) -> Self:
        builder = cls()
        tenant_id = activity.recipient.tenant_id
        if tenant_id is None and activity.channel_data is not None and activity.channel_data.tenant is not None:
            tenant_id = activity.channel_data.tenant.id

        builder.tenant_id(tenant_id)
        builder.conversation_id(activity.conversation.id)
        builder.conversation_item_link(activity.service_url)
        builder.channel_name(activity.channel_id)
        builder.user_id(activity.from_.aad_object_id)
        builder.user_name(activity.from_.name)
        builder.user_email(activity.from_.email)
        builder.agent_id(activity.recipient.agentic_app_id or activity.recipient.id)
        builder.agent_name(activity.recipient.name)
        builder.agentic_user_id(activity.recipient.agentic_user_id)
        builder.agentic_user_email(activity.recipient.email)
        builder.agent_description(activity.recipient.user_role)
        builder.agent_blueprint_id(activity.recipient.agentic_app_blueprint_id)
        return builder

    @classmethod
    def from_activity_context(cls, ctx: "ActivityContext[ActivityBase]") -> Self:
        return cls.from_activity(ctx.activity)

    def tenant_id(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.tenant_id, value)

    def conversation_id(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.conversation_id, value)

    def conversation_item_link(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.conversation_item_link, value)

    def channel_name(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.channel_name, value)

    def channel_link(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.channel_link, value)

    def agent_id(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.agent_id, value)

    def agent_name(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.agent_name, value)

    def agentic_user_id(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.agentic_user_id, value)

    def agent_blueprint_id(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.agent_blueprint_id, value)

    def user_name(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.user_name, value)

    def operation_source(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.operation_source, value)

    def invoke_agent_server(self, address: str | None, port: int | str | None = None) -> Self:
        self.set(APP_BAGGAGE_KEYS.server_address, address)
        if port is not None:
            self.set(APP_BAGGAGE_KEYS.server_port, str(port))
        return self

    def user_id(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.user_id, value)

    def user_email(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.user_email, value)

    def agent_description(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.agent_description, value)

    def agentic_user_email(self, value: str | None) -> Self:
        return self.set(APP_BAGGAGE_KEYS.agentic_user_email, value)

    def set(self, key: str, value: str | None) -> Self:
        normalized_key = key.strip()
        normalized_value = value.strip() if value is not None else None
        if normalized_key and normalized_value:
            self._entries[normalized_key] = normalized_value
        return self

    def build(self) -> AbstractContextManager[None]:
        return _TeamsBaggageScope(dict(self._entries))


@contextmanager
def with_teams_baggage(
    source: ActivityBase | ActivityContext[ActivityBase] | None = None,
    configure: Callable[[TeamsBaggageBuilder], None] | None = None,
) -> Iterator[None]:
    builder = TeamsBaggageBuilder()
    if isinstance(source, ActivityBase):
        builder = TeamsBaggageBuilder.from_activity(source)
    elif source is not None:
        builder = TeamsBaggageBuilder.from_activity_context(source)

    if configure is not None:
        configure(builder)

    with builder.build():
        yield
