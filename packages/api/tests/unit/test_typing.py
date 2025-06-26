"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft.teams.api.activities.typing import TypingActivity
from microsoft.teams.api.models import Account, ConversationAccount


@pytest.fixture
def user() -> Account:
    return Account(id="1", name="test", role="user")


@pytest.fixture
def bot() -> Account:
    return Account(id="2", name="test-bot", role="bot")


@pytest.fixture
def chat() -> ConversationAccount:
    return ConversationAccount(id="1", conversation_type="personal")


@pytest.mark.unit
class TestTyping:
    """Unit tests for Typing class."""

    def test_should_build(self, user: Account, bot: Account, chat: ConversationAccount) -> None:
        """Test basic activity construction."""
        activity = TypingActivity({"id": "1", "from": user, "conversation": chat, "recipient": bot})
        assert activity.type == "typing"
        assert activity.text is None

    def test_should_build_with_text(self, user: Account, bot: Account, chat: ConversationAccount) -> None:
        """Test activity construction with text manipulation."""
        activity = (
            TypingActivity({"id": "1", "from": user, "conversation": chat, "recipient": bot})
            .with_text("test")
            .add_text("ing123")
        )
        assert activity.type == "typing"
        assert activity.text == "testing123"
