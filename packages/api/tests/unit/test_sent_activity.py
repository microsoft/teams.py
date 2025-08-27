"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft.teams.api.activities import ActivityParams, MessageActivityInput, SentActivity


@pytest.fixture
def mock_new_activity_params() -> ActivityParams:
    """Create a mock ActivityParams for testing."""
    return MessageActivityInput(
        id="updated-id", type="message", text="updated message", locale="en-US", reply_to_id="activity-3"
    )


@pytest.fixture
def mock_sent_activity(mock_new_activity_params: ActivityParams) -> SentActivity:
    """Create a mock SentActivity for testing."""
    return SentActivity(
        id="sent-1",
        activity_params=mock_new_activity_params,
    )


@pytest.mark.unit
class TestSentActivity:
    """Unit tests for SentActivity class."""

    def test_should_merge_sent_activity(self, mock_sent_activity: SentActivity) -> None:
        old_params = MessageActivityInput(
            text="old message",
        )
        merged_activity = SentActivity.merge(old_params, mock_sent_activity)
        assert merged_activity.id == "sent-1"
        assert merged_activity.activity_params.id == "updated-id"
        assert merged_activity.activity_params.type == "message"
        assert merged_activity.activity_params.text == "updated message"
        assert merged_activity.activity_params.locale == "en-US"
        assert merged_activity.activity_params.reply_to_id == "activity-3"
