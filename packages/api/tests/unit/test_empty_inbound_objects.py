"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import Any, Dict

import pytest
from microsoft_teams.api.activities import ActivityTypeAdapter
from microsoft_teams.api.models.channel_data import ThreadInfo
from pydantic import ValidationError


def _activity(**overrides: Any) -> Dict[str, Any]:
    """A minimal inbound message activity, with room for per-case overrides."""
    activity: Dict[str, Any] = {
        "type": "message",
        "id": "activity-id",
        "text": "hello",
        "channelId": "msteams",
        "serviceUrl": "https://smba.trafficmanager.net/emea/tenant/",
        "from": {"id": "user-id"},
        "conversation": {"id": "conversation-id"},
        "recipient": {"id": "bot-id"},
    }
    activity.update(overrides)
    return activity


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"channelData": {"app": {}}}, id="channel_data_app"),
        pytest.param({"channelData": {"channel": {}}}, id="channel_data_channel"),
        pytest.param({"channelData": {"team": {}}}, id="channel_data_team"),
        pytest.param({"channelData": {"tenant": {}}}, id="channel_data_tenant"),
        pytest.param({"channelData": {"settings": {}}}, id="channel_data_settings"),
        pytest.param({"attachments": [{}]}, id="attachment"),
        pytest.param({"entities": [{}]}, id="entity"),
    ],
)
def test_activity_parses_when_nested_object_is_empty(overrides: Dict[str, Any]) -> None:
    """
    The service can send nested objects as empty objects. These are inbound-only models, so a
    missing field must not reject the whole activity.

    Regression test for https://github.com/microsoft/teams.py/issues/563, where a
    ``channelData.app`` of ``{}`` raised a ValidationError and the activity was dropped.
    """
    assert ActivityTypeAdapter.validate_python(_activity(**overrides)) is not None


def test_activity_parses_unrecognized_entity_type() -> None:
    """An entity type this SDK version predates must not reject the activity."""
    activity = ActivityTypeAdapter.validate_python(_activity(entities=[{"type": "someFutureEntity"}]))

    assert activity.entities is not None
    assert activity.entities[0].type == "someFutureEntity"


def test_populated_channel_data_is_preserved() -> None:
    """Relaxing the required fields must not stop populated values from being parsed."""
    activity = ActivityTypeAdapter.validate_python(
        _activity(
            channelData={
                "app": {"id": "app-id", "version": "1.2.3"},
                "channel": {"id": "channel-id"},
                "team": {"id": "team-id"},
                "tenant": {"id": "tenant-id"},
                "settings": {"selectedChannel": {"id": "selected-channel-id"}},
            }
        )
    )

    channel_data = activity.channel_data
    assert channel_data is not None
    assert channel_data.app is not None
    assert channel_data.app.id == "app-id"
    assert channel_data.app.version == "1.2.3"
    assert channel_data.channel is not None
    assert channel_data.channel.id == "channel-id"
    assert channel_data.team is not None
    assert channel_data.team.id == "team-id"
    assert channel_data.tenant is not None
    assert channel_data.tenant.id == "tenant-id"
    assert channel_data.settings is not None
    assert channel_data.settings.selected_channel is not None
    assert channel_data.settings.selected_channel.id == "selected-channel-id"


def test_absent_channel_data_still_parses() -> None:
    """The pre-existing behaviour for a wholly absent channelData must be unchanged."""
    assert ActivityTypeAdapter.validate_python(_activity()).channel_data is None


def test_inbound_thread_metadata_is_typed_and_read_only() -> None:
    activity = ActivityTypeAdapter.validate_python(_activity(channelData={"thread": {"id": "root-id"}}))

    assert activity.channel_data is not None
    assert isinstance(activity.channel_data.thread, ThreadInfo)
    assert activity.channel_data.thread.id == "root-id"
    with pytest.raises(ValidationError):
        activity.channel_data.thread.id = "different-root"
