"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class _ApiAttributeNames:
    activity_id: str = "activity.id"
    activity_type: str = "activity.type"
    auth_flow: str = "auth.flow"
    conversation_id: str = "conversation.id"
    operation: str = "operation"
    service_url: str = "service.url"


@dataclass(frozen=True)
class _ApiAuthFlows:
    agentic: str = "agentic"
    app_only: str = "app_only"


@dataclass(frozen=True)
class _ApiMetricNames:
    outbound_calls: str = "microsoft.teams.outbound.calls"
    outbound_errors: str = "microsoft.teams.outbound.errors"


@dataclass(frozen=True)
class _ApiOutboundOperations:
    create: str = "create"
    create_targeted: str = "create_targeted"
    delete: str = "delete"
    delete_targeted: str = "delete_targeted"
    reply: str = "reply"
    update: str = "update"
    update_targeted: str = "update_targeted"


@dataclass(frozen=True)
class _ApiSpanNames:
    api_client: str = "microsoft.teams.api.client"
    auth_outbound: str = "microsoft.teams.auth.outbound"


API_ATTRIBUTE_NAMES = _ApiAttributeNames()
API_AUTH_FLOWS = _ApiAuthFlows()
API_METRIC_NAMES = _ApiMetricNames()
API_OUTBOUND_OPERATIONS = _ApiOutboundOperations()
API_SPAN_NAMES = _ApiSpanNames()
