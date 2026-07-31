"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.api import Account, ConversationAccount
from microsoft_teams.api.activities.event.agent_lifecycle import (
    AgenticIdentityCreatedActivity,
    AgenticIdentityCreatedValue,
    AgenticIdentityEnabledActivity,
    AgenticIdentityEnabledValue,
    AgenticIdentityManagerUpdatedActivity,
    AgenticIdentityManagerUpdatedValue,
    AgentLifecycleManagerRef,
)
from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES


def _identity_created() -> AgenticIdentityCreatedActivity:
    return AgenticIdentityCreatedActivity(
        id="lifecycle-1",
        channel_id="agents",
        from_=Account(id="system", name="System"),
        conversation=ConversationAccount(id="conversation-1"),
        recipient=Account(id="agentic-user-1"),
        value=AgenticIdentityCreatedValue(agentic_user_id="agentic-user-1"),
    )


def _enabled() -> AgenticIdentityEnabledActivity:
    return AgenticIdentityEnabledActivity(
        id="lifecycle-2",
        channel_id="agents",
        from_=Account(id="system", name="System"),
        conversation=ConversationAccount(id="conversation-1"),
        recipient=Account(id="agentic-user-1"),
        value=AgenticIdentityEnabledValue(agentic_user_id="agentic-user-1", version=6),
    )


def _manager_updated() -> AgenticIdentityManagerUpdatedActivity:
    return AgenticIdentityManagerUpdatedActivity(
        id="lifecycle-3",
        channel_id="agents",
        from_=Account(id="system", name="System"),
        conversation=ConversationAccount(id="conversation-1"),
        recipient=Account(id="agentic-user-1"),
        value=AgenticIdentityManagerUpdatedValue(
            agentic_user_id="agentic-user-1", manager=AgentLifecycleManagerRef(manager_id="manager-1")
        ),
    )


def test_general_agent_lifecycle_route_matches_every_variant() -> None:
    selector = ACTIVITY_ROUTES["agent_lifecycle"].selector

    assert selector(_identity_created())
    assert selector(_enabled())
    assert selector(_manager_updated())


@pytest.mark.parametrize(
    "route_key,activity_factory",
    [
        ("agentic_identity_created", _identity_created),
        ("agentic_identity_enabled", _enabled),
        ("agentic_identity_manager_updated", _manager_updated),
    ],
)
def test_variant_route_matches_only_its_own_variant(route_key, activity_factory) -> None:
    activity = activity_factory()

    assert ACTIVITY_ROUTES[route_key].selector(activity)

    other_keys = [
        key
        for key in (
            "agentic_identity_created",
            "agentic_identity_enabled",
            "agentic_identity_manager_updated",
        )
        if key != route_key
    ]
    for other in other_keys:
        assert not ACTIVITY_ROUTES[other].selector(activity)
