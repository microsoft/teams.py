"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class _Agent365BaggageKeys:
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
    invoke_response_status: str = "invoke.response.status"
    oauth_callback_invoked: str = "oauth.callback.invoked"
    oauth_connection: str = "oauth.connection"
    oauth_error_type: str = "oauth.error.type"
    oauth_failure_code: str = "oauth.failure.code"
    oauth_operation: str = "oauth.operation"
    oauth_result: str = "oauth.result"
    service_url: str = "service.url"


@dataclass(frozen=True)
class _AppHandlerDispatches:
    invoke: str = "invoke"
    type: str = "type"


@dataclass(frozen=True)
class _AppMetricNames:
    activities_received: str = "microsoft.teams.activities.received"
    handler_dispatched: str = "microsoft.teams.handler.dispatched"
    handler_duration: str = "microsoft.teams.handler.duration"
    handler_failures: str = "microsoft.teams.handler.failures"
    handler_unmatched: str = "microsoft.teams.handler.unmatched"
    oauth_errors: str = "microsoft.teams.oauth.errors"
    oauth_operation_duration: str = "microsoft.teams.oauth.operation.duration"
    oauth_operations: str = "microsoft.teams.oauth.operations"
    turn_duration: str = "microsoft.teams.activity.process.duration"


@dataclass(frozen=True)
class _AppOAuthErrorTypes:
    exception: str = "exception"
    http_error: str = "http_error"


@dataclass(frozen=True)
class _AppOAuthOperations:
    signin_failure: str = "signin_failure"
    token_exchange: str = "token_exchange"
    verify_state: str = "verify_state"


@dataclass(frozen=True)
class _AppOAuthResults:
    failure: str = "failure"
    no_token: str = "no_token"
    notified: str = "notified"
    success: str = "success"


@dataclass(frozen=True)
class _AppSpanNames:
    handler: str = "microsoft.teams.handler"
    oauth_signin_failure: str = "microsoft.teams.oauth.signin_failure"
    oauth_token_exchange: str = "microsoft.teams.oauth.token_exchange"
    oauth_verify_state: str = "microsoft.teams.oauth.verify_state"
    turn: str = "microsoft.teams.activity.process"


AGENT365_BAGGAGE_KEYS = _Agent365BaggageKeys()
APP_ATTRIBUTE_NAMES = _AppAttributeNames()
APP_HANDLER_DISPATCHES = _AppHandlerDispatches()
APP_METRIC_NAMES = _AppMetricNames()
APP_OAUTH_ERROR_TYPES = _AppOAuthErrorTypes()
APP_OAUTH_OPERATIONS = _AppOAuthOperations()
APP_OAUTH_RESULTS = _AppOAuthResults()
APP_SPAN_NAMES = _AppSpanNames()
