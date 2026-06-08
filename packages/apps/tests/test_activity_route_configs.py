"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import Account, ConversationAccount, ConversationChannelData, ConversationUpdateActivity
from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES


def _conversation_update_activity(channel_data: ConversationChannelData | None = None) -> ConversationUpdateActivity:
    return ConversationUpdateActivity(
        id="conversation-update-1",
        from_=Account(id="user-1", name="Test User"),
        conversation=ConversationAccount(id="conversation-1", conversation_type="personal"),
        recipient=Account(id="bot-1", name="Test Bot"),
        channel_data=channel_data,
    )


def test_conversation_event_routes_ignore_missing_channel_data() -> None:
    activity = _conversation_update_activity()

    assert ACTIVITY_ROUTES["conversation_update"].selector(activity)
    assert not ACTIVITY_ROUTES["channel_created"].selector(activity)


def test_conversation_event_routes_match_event_type() -> None:
    activity = _conversation_update_activity(ConversationChannelData(event_type="channelCreated"))

    assert ACTIVITY_ROUTES["channel_created"].selector(activity)
    assert not ACTIVITY_ROUTES["channel_deleted"].selector(activity)
