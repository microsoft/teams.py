"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from datetime import datetime

import pytest
from microsoft_teams.api.activities.event.meeting_start import (
    MeetingStartEventValue,
)


@pytest.mark.unit
class TestMeetingStartEventValue:
    """Unit tests for MeetingStartEventValue serialization."""

    def test_deserialization_from_aliased_fields(self):
        """Test that MeetingStartEventValue correctly deserializes from aliased field names"""
        data = {
            "Id": "meeting-123-base64",
            "MeetingType": "Scheduled",
            "JoinUrl": "https://teams.microsoft.com/join/meeting-123",
            "Title": "Sprint Planning Meeting",
            "StartTime": "2024-01-15T14:30:00Z",
        }

        event_value = MeetingStartEventValue.model_validate(data)

        assert event_value.id == "meeting-123-base64"
        assert event_value.meeting_type == "Scheduled"
        assert event_value.join_url == "https://teams.microsoft.com/join/meeting-123"
        assert event_value.title == "Sprint Planning Meeting"
        assert isinstance(event_value.start_time, datetime)
        assert event_value.start_time.year == 2024
        assert event_value.start_time.month == 1
        assert event_value.start_time.day == 15
