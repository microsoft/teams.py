"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for ConversationUpdateActivity routing with optional channelData.
Issue #239: Ensure selectors handle None channelData gracefully.
"""

import pytest
from microsoft_teams.api.activities import ConversationUpdateActivity
from microsoft_teams.api.models import Account, ConversationAccount
from microsoft_teams.apps.routing.activity_route_configs import ACTIVITY_ROUTES


@pytest.mark.unit
class TestConversationUpdateRouting:
    """Test activity routing for ConversationUpdateActivity with optional channelData."""

    @pytest.fixture
    def conversation_update_without_channel_data(self) -> ConversationUpdateActivity:
        """Create a ConversationUpdateActivity without channelData (simulates Direct Line)."""
        return ConversationUpdateActivity(
            type="conversationUpdate",
            id="test-id",
            channel_id="directline",
            service_url="https://directline.botframework.com/",
            from_=Account(id="user-id", name="User"),
            conversation=ConversationAccount(id="conv-id"),
            recipient=Account(id="bot-id", name="Bot"),
            members_added=[Account(id="new-user", name="New User")],
            channel_data=None
        )

    @pytest.fixture
    def conversation_update_with_channel_data(self) -> ConversationUpdateActivity:
        """Create a ConversationUpdateActivity with channelData (simulates Teams)."""
        from microsoft_teams.api.activities.conversation import ConversationChannelData

        return ConversationUpdateActivity(
            type="conversationUpdate",
            id="test-id",
            channel_id="msteams",
            service_url="https://smba.trafficmanager.net/teams/",
            from_=Account(id="user-id", name="User"),
            conversation=ConversationAccount(id="conv-id"),
            recipient=Account(id="bot-id", name="Bot"),
            channel_data=ConversationChannelData(event_type="channelCreated")
        )

    def test_conversation_update_selector_matches_without_channel_data(
        self, conversation_update_without_channel_data: ConversationUpdateActivity
    ) -> None:
        """Test that conversation_update selector matches activities without channelData."""
        config = ACTIVITY_ROUTES["conversation_update"]
        assert config.selector(conversation_update_without_channel_data) is True

    def test_conversation_update_selector_matches_with_channel_data(
        self, conversation_update_with_channel_data: ConversationUpdateActivity
    ) -> None:
        """Test that conversation_update selector still matches activities with channelData."""
        config = ACTIVITY_ROUTES["conversation_update"]
        assert config.selector(conversation_update_with_channel_data) is True

    def test_channel_created_selector_rejects_without_channel_data(
        self, conversation_update_without_channel_data: ConversationUpdateActivity
    ) -> None:
        """Test that event-specific selectors reject activities without channelData."""
        config = ACTIVITY_ROUTES["channel_created"]
        # Should not match because channel_data is None
        assert config.selector(conversation_update_without_channel_data) is False

    def test_channel_created_selector_matches_with_correct_event(
        self, conversation_update_with_channel_data: ConversationUpdateActivity
    ) -> None:
        """Test that event-specific selectors match when channelData has correct event_type."""
        config = ACTIVITY_ROUTES["channel_created"]
        assert config.selector(conversation_update_with_channel_data) is True

    def test_all_conversation_event_selectors_handle_none_channel_data(
        self, conversation_update_without_channel_data: ConversationUpdateActivity
    ) -> None:
        """Test that all conversation event selectors gracefully handle None channelData."""
        # These selectors should all return False (not match) without raising errors
        event_routes = [
            "channel_created",
            "channel_deleted",
            "channel_renamed",
            "channel_restored",
            "team_archived",
            "team_deleted",
            "team_hard_deleted",
            "team_renamed",
            "team_restored",
            "team_unarchived",
        ]

        for route_name in event_routes:
            config = ACTIVITY_ROUTES[route_name]
            # Should not match, but should not raise an error
            assert config.selector(conversation_update_without_channel_data) is False
