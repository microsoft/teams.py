"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import json

import pytest
from microsoft_teams.api import ChannelData, MessageActivityInput, SourceInfo
from microsoft_teams.api.activities import ActivityTypeAdapter
from pydantic import ValidationError


def _inbound(channel_data: dict) -> dict:
    return {
        "type": "message",
        "id": "activity-id",
        "text": "hello",
        "channelId": "msteams",
        "serviceUrl": "https://smba.trafficmanager.net/emea/tenant/",
        "from": {"id": "user-id"},
        "conversation": {"id": "conversation-id"},
        "recipient": {"id": "bot-id"},
        "channelData": channel_data,
    }


class TestChannelDataSource:
    def test_exposes_the_source_of_an_inbound_activity(self):
        activity = ActivityTypeAdapter.validate_python(
            _inbound({"tenant": {"id": "tenant-1"}, "source": {"name": "message"}})
        )

        channel_data = activity.channel_data
        assert channel_data is not None
        assert isinstance(channel_data.source, SourceInfo)
        assert channel_data.source.name == "message"

    def test_other_fields_still_parse(self):
        channel_data = ChannelData.model_validate(
            {
                "tenant": {"id": "tenant-1"},
                "channel": {"id": "19:channel@thread.tacv2"},
                "chat": {"id": "19:chat@thread.v2"},
                "replyChain": {"id": "1700000000001"},
                "source": {"name": "compose"},
            }
        )

        assert channel_data.tenant is not None
        assert channel_data.tenant.id == "tenant-1"
        assert channel_data.channel is not None
        assert channel_data.channel.id == "19:channel@thread.tacv2"
        assert channel_data.chat is not None
        assert channel_data.chat.id == "19:chat@thread.v2"
        assert channel_data.reply_chain is not None
        assert channel_data.reply_chain.id == "1700000000001"
        assert channel_data.source is not None
        assert channel_data.source.name == "compose"

    def test_source_is_absent_when_not_sent(self):
        channel_data = ChannelData.model_validate({"tenant": {"id": "tenant-1"}})

        assert channel_data.source is None

    def test_source_is_absent_when_sent_null(self):
        channel_data = ChannelData.model_validate({"source": None})

        assert channel_data.source is None

    def test_name_is_absent_when_sent_empty(self):
        channel_data = ChannelData.model_validate({"source": {}})

        assert channel_data.source is not None
        assert channel_data.source.name is None

    def test_name_is_absent_when_sent_null(self):
        channel_data = ChannelData.model_validate({"source": {"name": None}})

        assert channel_data.source is not None
        assert channel_data.source.name is None

    def test_keeps_unknown_keys_of_the_source(self):
        channel_data = ChannelData.model_validate({"source": {"name": "message", "other": 1}})

        assert channel_data.source is not None
        assert channel_data.source.name == "message"
        assert channel_data.source.model_extra == {"other": 1}

    @pytest.mark.parametrize(
        "channel_data",
        [
            {"source": "message"},
            {"source": {"name": 5}},
            {"source": ["message"]},
        ],
    )
    def test_rejects_values_of_the_wrong_type(self, channel_data):
        with pytest.raises(ValidationError):
            ChannelData.model_validate(channel_data)

    def test_is_available_on_an_activity(self):
        activity = MessageActivityInput(text="hi").with_channel_data(ChannelData(source=SourceInfo(name="message")))

        assert activity.channel_data is not None
        assert activity.channel_data.source is not None
        assert activity.channel_data.source.name == "message"

    def test_serializes_with_camel_case_aliases(self):
        channel_data = ChannelData(source=SourceInfo(name="message"))

        assert json.loads(channel_data.model_dump_json(exclude_none=True)) == {"source": {"name": "message"}}
