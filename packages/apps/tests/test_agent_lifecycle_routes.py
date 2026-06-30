"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.api import Account, ConversationAccount
from microsoft_teams.api.activities.event.agent_lifecycle import (
    AgenticUserEnabledActivity,
    AgenticUserEnabledValue,
    AgenticUserIdentityCreatedActivity,
    AgenticUserIdentityCreatedValue,
    AgenticUserManagerUpdatedActivity,
    AgenticUserManagerUpdatedValue,
    AgentLifecycleManagerRef,
)
from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES


def _identity_created() -> AgenticUserIdentityCreatedActivity:
    return AgenticUserIdentityCreatedActivity(
        id="lifecycle-1",
        channel_id="agents",
        from_=Account(id="system", name="System"),
        conversation=ConversationAccount(id="conversation-1"),
        recipient=Account(id="agentic-user-1"),
        value=AgenticUserIdentityCreatedValue(agentic_user_id="agentic-user-1"),
    )


def _enabled() -> AgenticUserEnabledActivity:
    return AgenticUserEnabledActivity(
        id="lifecycle-2",
        channel_id="agents",
        from_=Account(id="system", name="System"),
        conversation=ConversationAccount(id="conversation-1"),
        recipient=Account(id="agentic-user-1"),
        value=AgenticUserEnabledValue(agentic_user_id="agentic-user-1", version=6),
    )


def _manager_updated() -> AgenticUserManagerUpdatedActivity:
    return AgenticUserManagerUpdatedActivity(
        id="lifecycle-3",
        channel_id="agents",
        from_=Account(id="system", name="System"),
        conversation=ConversationAccount(id="conversation-1"),
        recipient=Account(id="agentic-user-1"),
        value=AgenticUserManagerUpdatedValue(
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
        ("agentic_user_identity_created", _identity_created),
        ("agentic_user_enabled", _enabled),
        ("agentic_user_manager_updated", _manager_updated),
    ],
)
def test_variant_route_matches_only_its_own_variant(route_key, activity_factory) -> None:
    activity = activity_factory()

    assert ACTIVITY_ROUTES[route_key].selector(activity)

    other_keys = [
        key
        for key in (
            "agentic_user_identity_created",
            "agentic_user_enabled",
            "agentic_user_manager_updated",
        )
        if key != route_key
    ]
    for other in other_keys:
        assert not ACTIVITY_ROUTES[other].selector(activity)
