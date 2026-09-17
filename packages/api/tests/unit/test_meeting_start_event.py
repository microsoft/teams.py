"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from datetime import datetime

import pytest
from microsoft_teams.api.activities import ActivityTypeAdapter
from microsoft_teams.api.activities.event.meeting_start import (
    MeetingStartEventActivity,
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

    def test_deserialization_with_null_join_url(self):
        """Meetings held inside a channel send a null JoinUrl, which must still validate."""
        payload = {
            "type": "event",
            "name": "application/vnd.microsoft.meetingStart",
            "id": "activity-id",
            "channelId": "msteams",
            "serviceUrl": "https://smba.trafficmanager.net/amer/",
            "from": {"id": "user-id"},
            "conversation": {"id": "19:meeting-thread@thread.tacv2", "conversationType": "channel"},
            "recipient": {"id": "bot-id"},
            "value": {
                "MeetingType": "",
                "Title": 'Meeting in "General" ',
                "Id": "meeting-123-base64",
                "JoinUrl": None,
                "StartTime": "2026-09-17T17:40:13.081877Z",
            },
        }

        activity = ActivityTypeAdapter.validate_python(payload)

        assert isinstance(activity, MeetingStartEventActivity)
        assert activity.value.join_url is None
        assert activity.value.title == 'Meeting in "General" '
