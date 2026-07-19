"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class _AppBaggageKeys:
    agent_blueprint_id: str = "microsoft.a365.agent.blueprint.id"
    agent_description: str = "gen_ai.agent.description"
    agent_id: str = "gen_ai.agent.id"
    agent_name: str = "gen_ai.agent.name"
    agentic_user_email: str = "microsoft.agent.user.email"
    agentic_user_id: str = "microsoft.agent.user.id"
    channel_link: str = "microsoft.channel.link"
    channel_name: str = "microsoft.channel.name"
    conversation_id: str = "gen_ai.conversation.id"
    conversation_item_link: str = "microsoft.conversation.item.link"
    operation_source: str = "service.name"
    server_address: str = "server.address"
    server_port: str = "server.port"
    tenant_id: str = "microsoft.tenant.id"
    user_email: str = "user.email"
    user_id: str = "user.id"
    user_name: str = "user.name"


@dataclass(frozen=True)
class _AppAttributeNames:
    activity_id: str = "activity.id"
    activity_type: str = "activity.type"
    bot_id: str = "bot.id"
    channel_id: str = "channel.id"
    conversation_id: str = "conversation.id"
    handler_dispatch: str = "handler.dispatch"
    handler_type: str = "handler.type"
    invoke_name: str = "invoke.name"
    service_url: str = "service.url"


@dataclass(frozen=True)
class _AppHandlerDispatches:
    invoke: str = "invoke"
    type: str = "type"


@dataclass(frozen=True)
class _AppMetricNames:
    activities_received: str = "teams.activities.received"
    handler_dispatched: str = "teams.handler.dispatched"
    handler_duration: str = "teams.handler.duration"
    handler_failures: str = "teams.handler.failures"
    handler_unmatched: str = "teams.handler.unmatched"
    turn_duration: str = "teams.turn.duration"


@dataclass(frozen=True)
class _AppSpanNames:
    handler: str = "handler"
    turn: str = "turn"


APP_BAGGAGE_KEYS = _AppBaggageKeys()
APP_ATTRIBUTE_NAMES = _AppAttributeNames()
APP_HANDLER_DISPATCHES = _AppHandlerDispatches()
APP_METRIC_NAMES = _AppMetricNames()
APP_SPAN_NAMES = _AppSpanNames()
