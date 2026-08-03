"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft_teams.api.models import Conversation, ConversationAccount


@pytest.mark.unit
class TestConversationType:
    """Unit tests for the shared ConversationType open union on Conversation and ConversationAccount."""

    def test_conversation_accepts_channel(self) -> None:
        """Regression: a 'channel' conversation must validate.

        The previous closed Literal["personal", "groupChat"] rejected 'channel', and
        CustomBaseModel's extra='allow' does not relax Literal validation, so a channel
        conversation failed validation.
        """
        conversation = Conversation.model_validate({"id": "c1", "conversationType": "channel"})
        assert conversation.conversation_type == "channel"

    @pytest.mark.parametrize("value", ["personal", "groupChat", "channel"])
    def test_conversation_known_values_round_trip(self, value: str) -> None:
        conversation = Conversation.model_validate({"id": "c1", "conversationType": value})
        assert conversation.conversation_type == value
        assert conversation.model_dump(by_alias=True, exclude_none=True)["conversationType"] == value

    def test_conversation_accepts_unknown_value(self) -> None:
        """The open union stays forward-compatible with values the SDK has not enumerated."""
        conversation = Conversation.model_validate({"id": "c1", "conversationType": "someFutureScope"})
        assert conversation.conversation_type == "someFutureScope"

    def test_conversation_account_accepts_channel(self) -> None:
        account = ConversationAccount.model_validate({"id": "c1", "conversationType": "channel"})
        assert account.conversation_type == "channel"

    def test_conversation_account_type_is_optional(self) -> None:
        account = ConversationAccount.model_validate({"id": "c1"})
        assert account.conversation_type is None
