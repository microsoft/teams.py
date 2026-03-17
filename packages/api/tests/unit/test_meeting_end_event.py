"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from datetime import datetime

import pytest
from microsoft_teams.api.activities.event.meeting_end import (
    MeetingEndEventValue,
)


@pytest.mark.unit
class TestMeetingEndEventValue:
    """Unit tests for MeetingEndEventValue serialization."""

    def test_deserialization_from_aliased_fields(self):
        """Test that MeetingEndEventValue correctly deserializes from aliased field names"""
        data = {
            "Id": "meeting-123-base64",
            "MeetingType": "Scheduled",
            "JoinUrl": "https://teams.microsoft.com/join/meeting-123",
            "Title": "Sprint Planning Meeting",
            "EndTime": "2024-01-15T15:30:00Z",
        }

        event_value = MeetingEndEventValue.model_validate(data)
        assert event_value.id == "meeting-123-base64"
        assert event_value.meeting_type == "Scheduled"
        assert event_value.join_url == "https://teams.microsoft.com/join/meeting-123"
        assert event_value.title == "Sprint Planning Meeting"
        assert isinstance(event_value.end_time, datetime)
        assert event_value.end_time.year == 2024
        assert event_value.end_time.month == 1
        assert event_value.end_time.day == 15
