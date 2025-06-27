"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime

import pytest
from microsoft.teams.api.activities.activity import Activity, CitationAppearance
from microsoft.teams.api.models import (
    Account,
    ChannelData,
    ChannelInfo,
    CitationIconName,
    ConversationAccount,
    ConversationReference,
    MeetingInfo,
    NotificationInfo,
    TeamInfo,
    TenantInfo,
)


@pytest.fixture
def user() -> Account:
    return Account(id="1", name="test", role="user")


@pytest.fixture
def bot() -> Account:
    return Account(id="2", name="test-bot", role="bot")


@pytest.fixture
def chat() -> ConversationAccount:
    return ConversationAccount(id="1", conversation_type="personal")


@pytest.fixture
def fixture_activity() -> Activity:
    class FixtureActivity(Activity):
        @property
        def type(self) -> str:
            return self._type

    return FixtureActivity


@pytest.mark.unit
class TestActivity:
    """Unit tests for Activity class."""

    def test_should_build(
        self, fixture_activity: Activity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = (
            fixture_activity({"type": "test", "id": "1", "from": user, "conversation": chat, "recipient": bot})
            .with_locale("en")
            .with_relates_to(
                ConversationReference(
                    channel_id="msteams",
                    service_url="http://localhost",
                    bot=bot,
                    conversation=chat,
                )
            )
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
        assert activity.relates_to == ConversationReference(
            channel_id="msteams",
            service_url="http://localhost",
            bot=bot,
            conversation=chat,
        )
        assert activity.recipient == bot
        assert activity.reply_to_id == "3"
        assert activity.service_url == "http://localhost"
        assert activity.timestamp is not None
        assert activity.local_timestamp is not None

    def test_should_have_channel_data_accessors(
        self, fixture_activity: Activity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = (
            fixture_activity({"type": "test", "id": "1", "from": user, "conversation": chat, "recipient": bot})
            .with_locale("en")
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
        assert activity.channel.id == "channel-id"
        assert activity.team.id == "team-id"
        assert activity.meeting.id == "meeting-id"
        assert activity.notification.alert is True

    def test_should_add_ai_label(
        self, fixture_activity: Activity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = fixture_activity(
            {"type": "test", "id": "1", "from": user, "conversation": chat, "recipient": bot}
        ).add_ai_generated()

        assert activity.type == "test"
        assert len(activity.entities) == 1
        assert activity.entities[0].additional_type[0] == "AIGeneratedContent"

    def test_should_add_feedback_label(
        self, fixture_activity: Activity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = fixture_activity(
            {"type": "test", "id": "1", "from": user, "conversation": chat, "recipient": bot}
        ).add_feedback()

        assert activity.type == "test"
        assert activity.channel_data.feedback_loop_enabled is True

    def test_should_add_citation(
        self, fixture_activity: Activity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = fixture_activity(
            {"type": "test", "id": "1", "from": user, "conversation": chat, "recipient": bot}
        ).add_citation(0, CitationAppearance(abstract="test", name="test"))

        assert activity.type == "test"
        assert len(activity.entities) == 1
        assert len(activity.entities[0].citation) == 1

    def test_should_add_citation_with_icon(
        self, fixture_activity: Activity, user: Account, bot: Account, chat: ConversationAccount
    ) -> None:
        activity = fixture_activity(
            {"type": "test", "id": "1", "from": user, "conversation": chat, "recipient": bot}
        ).add_citation(0, CitationAppearance(abstract="test", name="test", icon=CitationIconName.GIF))

        assert activity.type == "test"
        assert len(activity.entities) == 1
        assert activity.entities[0].citation[0].appearance.abstract == "test"
        assert activity.entities[0].citation[0].appearance.name == "test"
        assert activity.entities[0].citation[0].appearance.image.name == "GIF"
