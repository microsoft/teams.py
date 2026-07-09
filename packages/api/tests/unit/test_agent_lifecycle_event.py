"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import Any, Dict

import pytest
from microsoft_teams.api.activities import ActivityTypeAdapter
from microsoft_teams.api.activities.event.agent_lifecycle import (
    AgenticUserDeletedActivity,
    AgenticUserDisabledActivity,
    AgenticUserEnabledActivity,
    AgenticUserIdentityCreatedActivity,
    AgenticUserIdentityUpdatedActivity,
    AgenticUserManagerUpdatedActivity,
    AgenticUserUndeletedActivity,
    AgenticUserWorkloadOnboardingUpdatedActivity,
)

# Static sample IDs for unit-test payloads; these tests do not call live services.
TENANT_ID = "00000000-0000-0000-0000-000000000001"
AGENTIC_USER_ID = "00000000-0000-0000-0000-000000000002"
AGENTIC_APP_INSTANCE_ID = "00000000-0000-0000-0000-000000000003"
BLUEPRINT_ID = "00000000-0000-0000-0000-000000000004"


def _envelope(value: Dict[str, Any], value_type: str) -> Dict[str, Any]:
    return {
        "recipient": {
            "agenticUserId": AGENTIC_USER_ID,
            "agenticAppId": AGENTIC_APP_INSTANCE_ID,
            "agenticAppBlueprintId": BLUEPRINT_ID,
            "callbackUri": "https://example.test/api/messages",
            "tenantId": TENANT_ID,
            "role": "agenticUser",
            "id": AGENTIC_USER_ID,
        },
        "type": "event",
        "id": "activity-id",
        "timestamp": "2026-06-29T00:00:00Z",
        "serviceUrl": "https://smba.trafficmanager.net/amer/tenant/",
        "channelId": "agents",
        "from": {"id": "system", "name": "System", "tenantId": TENANT_ID},
        "conversation": {"tenantId": TENANT_ID, "id": "conversation-id", "topic": None},
        "channelData": {"tenant": {"id": TENANT_ID}, "productContext": None},
        "valueType": value_type,
        "value": value,
        "name": "agentLifecycle",
    }


def _common(event_type: str) -> Dict[str, Any]:
    return {
        "tenantId": TENANT_ID,
        "agenticUserId": AGENTIC_USER_ID,
        "agenticAppInstanceId": AGENTIC_APP_INSTANCE_ID,
        "agentIdentityBlueprintId": BLUEPRINT_ID,
        "eventType": event_type,
    }


@pytest.mark.unit
class TestAgentLifecycleEventParsing:
    def test_identity_created(self) -> None:
        value = {
            "expirationDateTime": "0001-01-01T00:00:00+00:00",
            "manager": {
                "displayName": None,
                "userId": "3c22b565-74f3-48b0-aa18-1dc03b8ec270",
                "email": "manager@example.test",
            },
            **_common("agenticUserIdentityCreated"),
        }
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserIdentityCreated"))

        assert isinstance(activity, AgenticUserIdentityCreatedActivity)
        assert activity.name == "agentLifecycle"
        assert activity.value_type == "AgenticUserIdentityCreated"
        assert activity.value.agentic_user_id == AGENTIC_USER_ID
        assert activity.value.manager is not None
        assert activity.value.manager.user_id == "3c22b565-74f3-48b0-aa18-1dc03b8ec270"
        assert activity.value.manager.email == "manager@example.test"

    @pytest.mark.parametrize(
        "property_name,property_value",
        [
            ("Mail", "newinstance4@teamssdk.onmicrosoft.com"),
            ("Alias", "newinstance4"),
            ("UserPrincipalName", "newinstance4@teamssdk.onmicrosoft.com"),
        ],
    )
    def test_identity_updated(self, property_name: str, property_value: str) -> None:
        value = {
            "updatedProperty": {"propertyName": property_name, "propertyValue": property_value},
            **_common("agenticUserIdentityUpdated"),
            "version": 4,
        }
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserIdentityUpdated"))

        assert isinstance(activity, AgenticUserIdentityUpdatedActivity)
        assert activity.value.updated_property.property_name == property_name
        assert activity.value.updated_property.property_value == property_value
        assert activity.value.version == 4

    def test_manager_updated(self) -> None:
        value = {
            "manager": {"managerId": "3c22b565-74f3-48b0-aa18-1dc03b8ec270"},
            **_common("agenticUserManagerUpdated"),
            "version": 6,
        }
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserManagerUpdated"))

        assert isinstance(activity, AgenticUserManagerUpdatedActivity)
        assert activity.value.manager is not None
        assert activity.value.manager.manager_id == "3c22b565-74f3-48b0-aa18-1dc03b8ec270"
        assert activity.value.version == 6

    def test_enabled(self) -> None:
        value = {**_common("agenticUserEnabled"), "version": 6}
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserEnabled"))

        assert isinstance(activity, AgenticUserEnabledActivity)
        assert activity.value.version == 6

    def test_disabled(self) -> None:
        value = {**_common("agenticUserDisabled"), "version": 7}
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserDisabled"))

        assert isinstance(activity, AgenticUserDisabledActivity)

    def test_deleted(self) -> None:
        value = {**_common("agenticUserDeleted"), "deletionReason": "UserSoftDelete", "version": 8}
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserDeleted"))

        assert isinstance(activity, AgenticUserDeletedActivity)
        assert activity.value.deletion_reason == "UserSoftDelete"

    def test_undeleted(self) -> None:
        value = {**_common("agenticUserUndeleted"), "version": 9}
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserUndeleted"))

        assert isinstance(activity, AgenticUserUndeletedActivity)

    def test_workload_onboarding_updated(self) -> None:
        value = {
            "workloadName": "Teams",
            "workloadOnboardingState": "succeeded",
            **_common("agenticUserWorkloadOnboardingUpdated"),
        }
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserWorkloadOnboardingUpdated"))

        assert isinstance(activity, AgenticUserWorkloadOnboardingUpdatedActivity)
        assert activity.value.workload_name == "Teams"
        assert activity.value.workload_onboarding_state == "succeeded"

    def test_round_trip_serialization_uses_camel_case(self) -> None:
        value = {
            "manager": {"managerId": "3c22b565-74f3-48b0-aa18-1dc03b8ec270"},
            **_common("agenticUserManagerUpdated"),
            "version": 6,
        }
        activity = ActivityTypeAdapter.validate_python(_envelope(value, "AgenticUserManagerUpdated"))
        dumped = activity.model_dump(by_alias=True, exclude_none=True)

        assert dumped["name"] == "agentLifecycle"
        assert dumped["valueType"] == "AgenticUserManagerUpdated"
        assert dumped["value"]["agenticAppInstanceId"] == AGENTIC_APP_INSTANCE_ID
        assert dumped["value"]["manager"]["managerId"] == "3c22b565-74f3-48b0-aa18-1dc03b8ec270"
