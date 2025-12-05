"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from datetime import datetime

import pytest
from microsoft_teams.api.activities import MessageReactionActivityInput
from microsoft_teams.api.models import (
    Account,
    MessageReaction,
)


@pytest.fixture
def mock_reaction_activity(mock_account: Account) -> MessageReactionActivityInput:
    """Create a mock MessageReactionActivityInput for testing."""
    return MessageReactionActivityInput(
        id="1",
        from_=mock_account,
        type="messageReaction",
        timestamp=datetime.now(),
        reactions_added=[],
        reactions_removed=[],
    )


@pytest.mark.unit
class TestMessageReactionActivityInput:
    """Unit tests for MessageReactionActivityInput class."""

    def test_should_update_reaction_activity(
        self, mock_reaction_activity: MessageReactionActivityInput, mock_account: Account
    ) -> None:
        updated_activity = mock_reaction_activity.with_recipient(mock_account).with_service_url("http://localhost")
        assert updated_activity.recipient == mock_account
        assert updated_activity.service_url == "http://localhost"

    def test_should_add_reaction(self, mock_reaction_activity: MessageReactionActivityInput) -> None:
        reaction = MessageReaction(type="like")
        mock_reaction_activity.add_reaction(reaction)
        assert mock_reaction_activity.reactions_added and len(mock_reaction_activity.reactions_added) == 1
        assert mock_reaction_activity.reactions_added[0].type == "like"

    def test_should_remove_reaction(self, mock_reaction_activity: MessageReactionActivityInput) -> None:
        reaction = MessageReaction(type="like")
        mock_reaction_activity.add_reaction(reaction)
        mock_reaction_activity.remove_reaction(reaction)
        assert not mock_reaction_activity.reactions_added
        assert mock_reaction_activity.reactions_removed and len(mock_reaction_activity.reactions_removed) == 1
        assert mock_reaction_activity.reactions_removed[0].type == "like"
