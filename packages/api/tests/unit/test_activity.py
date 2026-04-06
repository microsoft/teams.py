"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from datetime import datetime

import pytest
from microsoft_teams.api.models import (
    Account,
    ActivityInputBase,
    ChannelData,
    ChannelInfo,
    ConversationAccount,
    MeetingInfo,
    NotificationInfo,
    TeamInfo,
    TenantInfo,
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
            .with_reply_to_id("3")
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
        assert activity.reply_to_id == "3"
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
