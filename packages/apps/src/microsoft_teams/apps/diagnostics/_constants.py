"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


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
    plugin: str = "plugin"
    route: str = "route"


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


APP_ATTRIBUTE_NAMES = _AppAttributeNames()
APP_HANDLER_DISPATCHES = _AppHandlerDispatches()
APP_METRIC_NAMES = _AppMetricNames()
APP_SPAN_NAMES = _AppSpanNames()
