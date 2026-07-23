"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from datetime import datetime

import pytest
from microsoft_teams.api.activities import ActivityTypeAdapter, ConversationUpdateActivity, MessageActivity
from microsoft_teams.api.models import (
    Account,
    ActivityInputBase,
    ChannelData,
    ChannelInfo,
    ConversationAccount,
    MeetingInfo,
    MentionEntity,
    NotificationInfo,
    TeamInfo,
    TenantInfo,
    UnknownEntity,
)


@pytest.fixture
def user() -> Account:
    return Account(id="1", name="test")


@pytest.fixture
def bot() -> Account:
    return Account(id="2", name="test-bot")


@pytest.fixture
def chat() -> ConversationAccount:
    return ConversationAccount(id="1", conversation_type="personal")


class ConcreteTestActivity(ActivityInputBase):
    """Concrete Activity implementation for testing."""

    type: str = "test"


@pytest.fixture
def test_activity(user: Account, bot: Account, chat: ConversationAccount) -> ConcreteTestActivity:
    """Create a test activity with required fields set."""
    activity = ConcreteTestActivity(
        id="1",
        from_=user,
        conversation=chat,
        recipient=bot,
    )
    return activity


@pytest.mark.unit
class TestActivity:
    """Unit tests for Activity class."""

    def test_should_build(
        self, test_activity: ConcreteTestActivity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = (
            test_activity.with_locale("en")
            .with_recipient(bot)
            .with_service_url("http://localhost")
            .with_timestamp(datetime.now())
            .with_local_timestamp(datetime.now())
        )

        assert activity.id == "1"
        assert activity.type == "test"
        assert activity.locale == "en"
        assert activity.from_ == user
        assert activity.conversation == chat
        assert activity.recipient == bot
        assert activity.service_url == "http://localhost"
        assert activity.timestamp is not None
        assert activity.local_timestamp is not None

    def test_should_have_channel_data_accessors(
        self, test_activity: ConcreteTestActivity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = (
            test_activity.with_locale("en")
            .with_from(user)
            .with_channel_data(
                ChannelData(
                    tenant=TenantInfo(id="tenant-id"),
                    channel=ChannelInfo(id="channel-id"),
                    team=TeamInfo(id="team-id"),
                    meeting=MeetingInfo(id="meeting-id"),
                    notification=NotificationInfo(alert=True),
                )
            )
        )

        assert activity.id == "1"
        assert activity.type == "test"
        assert activity.locale == "en"
        assert activity.from_ == user
        assert activity.conversation == chat
        assert activity.recipient == bot
        assert activity.tenant.id == "tenant-id"
        assert activity.channel and activity.channel.id == "channel-id"
        assert activity.team and activity.team.id == "team-id"
        assert activity.meeting and activity.meeting.id == "meeting-id"
        assert activity.notification and activity.notification.alert is True


@pytest.mark.unit
class TestActivityTypeAdapter:
    """Unit tests for ActivityTypeAdapter behavior."""

    def test_accepts_unknown_entity_types(self) -> None:
        payload = {
            "type": "message",
            "id": "msg-unknown-1",
            "from": {"id": "user-123", "name": "Test User"},
            "conversation": {"id": "conv-456", "conversationType": "personal"},
            "recipient": {"id": "bot-789", "name": "Test Bot"},
            "entities": [
                {
                    "type": "ClientCapabilities",
                    "supportsListening": True,
                    "supportsSplashScreen": True,
                    "supportsTts": True,
                },
                {
                    "type": "mention",
                    "mentioned": {"id": "user-123", "name": "Test User"},
                    "text": "<at>Test User</at>",
                },
            ],
        }

        activity = ActivityTypeAdapter.validate_python(payload)

        assert isinstance(activity, MessageActivity)
        assert activity.entities is not None
        assert len(activity.entities) == 2
        assert isinstance(activity.entities[0], UnknownEntity)
        assert activity.entities[0].type == "ClientCapabilities"
        assert activity.entities[0].model_dump().get("supportsListening") is True
        assert isinstance(activity.entities[1], MentionEntity)

    def test_conversation_update_without_channel_data(self) -> None:
        payload = {
            "type": "conversationUpdate",
            "id": "conv-update-1",
            "from": {"id": "user-123", "name": "Test User"},
            "conversation": {"id": "conv-456", "conversationType": "personal"},
            "recipient": {"id": "bot-789", "name": "Test Bot"},
        }

        activity = ActivityTypeAdapter.validate_python(payload)

        assert isinstance(activity, ConversationUpdateActivity)
        assert activity.channel_data is None

    def test_conversation_update_channel_member_added(self) -> None:
        # Regression test for private/shared channel membership events (issue #520):
        # Teams emits channelMemberAdded / channelMemberRemoved for private and shared
        # channels, which previously failed strict Literal validation.
        payload = {
            "type": "conversationUpdate",
            "id": "conv-update-channel-member",
            "from": {"id": "user-123", "name": "Test User"},
            "conversation": {"id": "conv-456", "conversationType": "channel"},
            "recipient": {"id": "bot-789", "name": "Test Bot"},
            "channelData": {"eventType": "channelMemberAdded"},
        }

        activity = ActivityTypeAdapter.validate_python(payload)

        assert isinstance(activity, ConversationUpdateActivity)
        assert activity.channel_data is not None
        assert activity.channel_data.event_type == "channelMemberAdded"

    def test_conversation_update_unknown_event_type(self) -> None:
        # Unknown / newly introduced event types must not fail validation; the raw
        # value is preserved so callers can inspect it.
        payload = {
            "type": "conversationUpdate",
            "id": "conv-update-unknown-event",
            "from": {"id": "user-123", "name": "Test User"},
            "conversation": {"id": "conv-456", "conversationType": "channel"},
            "recipient": {"id": "bot-789", "name": "Test Bot"},
            "channelData": {"eventType": "someFutureEventType"},
        }

        activity = ActivityTypeAdapter.validate_python(payload)

        assert isinstance(activity, ConversationUpdateActivity)
        assert activity.channel_data is not None
        assert activity.channel_data.event_type == "someFutureEventType"
