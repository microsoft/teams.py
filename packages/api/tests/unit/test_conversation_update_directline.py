"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for ConversationUpdateActivity with Direct Line API 3.0 compatibility.
Issue #239: Direct Line sends conversationUpdate without channelData field.
"""

import pytest
from microsoft_teams.api.activities import ActivityTypeAdapter, ConversationUpdateActivity
from microsoft_teams.api.activities.conversation import ConversationUpdateActivityInput
from microsoft_teams.api.models import Account, ConversationAccount


@pytest.mark.unit
class TestConversationUpdateDirectLine:
    """Test ConversationUpdateActivity compatibility with Direct Line API 3.0."""

    def test_parse_conversation_update_without_channel_data(self) -> None:
        """Test that ConversationUpdateActivity can be parsed without channelData field.

        This simulates the payload sent by Direct Line API 3.0 when starting a conversation.
        Direct Line automatically sends conversationUpdate activities without channelData,
        which should be accepted by the SDK.
        """
        # Payload simulating Direct Line conversationUpdate (no channelData)
        payload = {
            "type": "conversationUpdate",
            "id": "Bh0ETfRaC25",
            "timestamp": "2025-12-22T11:29:37.3485747Z",
            "serviceUrl": "https://directline.botframework.com/",
            "channelId": "directline",
            "from": {
                "id": "dl_aba7a98ada0ee99e7d54af5df8e00440",
                "name": "Bot Tester"
            },
            "conversation": {
                "id": "conv123"
            },
            "recipient": {
                "id": "bot-id",
                "name": "Test Bot"
            },
            "membersAdded": [
                {
                    "id": "user123",
                    "name": "Test User"
                }
            ]
        }

        # This should NOT raise a validation error
        activity = ActivityTypeAdapter.validate_python(payload)

        # Verify it's a ConversationUpdateActivity
        assert isinstance(activity, ConversationUpdateActivity)
        assert activity.type == "conversationUpdate"
        assert activity.channel_id == "directline"
        assert activity.channel_data is None
        assert activity.members_added is not None
        assert len(activity.members_added) == 1
        assert activity.members_added[0].id == "user123"

    def test_parse_conversation_update_with_channel_data(self) -> None:
        """Test that ConversationUpdateActivity still works with channelData (Teams behavior)."""
        payload = {
            "type": "conversationUpdate",
            "id": "test-id",
            "timestamp": "2025-12-22T11:29:37.3485747Z",
            "serviceUrl": "https://smba.trafficmanager.net/teams/",
            "channelId": "msteams",
            "from": {
                "id": "bot-id",
                "name": "Test Bot"
            },
            "conversation": {
                "id": "conv123"
            },
            "recipient": {
                "id": "user-id",
                "name": "Test User"
            },
            "channelData": {
                "eventType": "channelCreated",
                "tenant": {
                    "id": "tenant-id"
                }
            }
        }

        activity = ActivityTypeAdapter.validate_python(payload)

        assert isinstance(activity, ConversationUpdateActivity)
        assert activity.type == "conversationUpdate"
        assert activity.channel_id == "msteams"
        assert activity.channel_data is not None
        assert activity.channel_data.event_type == "channelCreated"

    def test_conversation_update_input_without_channel_data(self) -> None:
        """Test creating ConversationUpdateActivityInput without channelData."""
        # Create activity input without channel_data
        activity = ConversationUpdateActivityInput(
            from_=Account(id="user-id", name="User"),
            conversation=ConversationAccount(id="conv-id"),
            recipient=Account(id="bot-id", name="Bot"),
            members_added=[Account(id="new-user", name="New User")]
        )

        assert activity.type == "conversationUpdate"
        assert activity.channel_data is None
        assert activity.members_added is not None
        assert len(activity.members_added) == 1
