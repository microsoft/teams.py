"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import json

import pytest
from microsoft_teams.api import (
    ChannelData,
    ChatInfo,
    EncryptedChatInfo,
    MessageActivityInput,
    ReplyChainInfo,
)
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


class TestChannelDataChatAndReplyChain:
    def test_exposes_the_ids_of_an_inbound_activity(self):
        activity = ActivityTypeAdapter.validate_python(
            _inbound(
                {
                    "tenant": {"id": "tenant-1"},
                    "chat": {"id": "19:user_bot@unq.gbl.spaces", "encrypted": {"id": "a:encrypted"}},
                    "replyChain": {"id": "1700000000001"},
                }
            )
        )

        channel_data = activity.channel_data
        assert channel_data is not None
        assert isinstance(channel_data.chat, ChatInfo)
        assert isinstance(channel_data.chat.encrypted, EncryptedChatInfo)
        assert isinstance(channel_data.reply_chain, ReplyChainInfo)
        assert channel_data.chat.id == "19:user_bot@unq.gbl.spaces"
        assert channel_data.chat.encrypted.id == "a:encrypted"
        assert channel_data.reply_chain.id == "1700000000001"

    def test_ids_are_absent_when_not_sent(self):
        channel_data = ChannelData.model_validate({"tenant": {"id": "tenant-1"}})

        assert channel_data.chat is None
        assert channel_data.reply_chain is None

    def test_ids_are_absent_when_sent_empty(self):
        channel_data = ChannelData.model_validate({"chat": {}, "replyChain": {}})

        assert channel_data.chat is not None
        assert channel_data.chat.id is None
        assert channel_data.chat.encrypted is None
        assert channel_data.reply_chain is not None
        assert channel_data.reply_chain.id is None

    def test_encrypted_id_is_absent_when_not_sent(self):
        channel_data = ChannelData.model_validate({"chat": {"id": "19:user_bot@unq.gbl.spaces", "encrypted": {}}})

        assert channel_data.chat is not None
        assert channel_data.chat.encrypted is not None
        assert channel_data.chat.encrypted.id is None

    def test_keeps_the_chat_id_and_the_channel_id_apart(self):
        channel_data = ChannelData.model_validate(
            {"chat": {"id": "19:chat@thread.v2"}, "channel": {"id": "19:channel@thread.tacv2"}}
        )

        assert channel_data.chat is not None
        assert channel_data.channel is not None
        assert channel_data.chat.id == "19:chat@thread.v2"
        assert channel_data.channel.id == "19:channel@thread.tacv2"

    def test_is_read_only(self):
        channel_data = ChannelData.model_validate(
            {"chat": {"id": "19:chat@thread.v2", "encrypted": {"id": "a:encrypted"}}, "replyChain": {"id": "root-1"}}
        )

        assert channel_data.chat is not None
        assert channel_data.chat.encrypted is not None
        assert channel_data.reply_chain is not None
        with pytest.raises(ValidationError):
            channel_data.chat.id = "other"
        with pytest.raises(ValidationError):
            channel_data.chat.encrypted = EncryptedChatInfo(id="other")
        with pytest.raises(ValidationError):
            channel_data.chat.encrypted.id = "other"
        with pytest.raises(ValidationError):
            channel_data.reply_chain.id = "other"

    @pytest.mark.parametrize(
        "channel_data",
        [
            {"chat": {"id": 123}},
            {"chat": {"encrypted": "a:encrypted"}},
            {"chat": {"encrypted": {"id": 123}}},
            {"chat": "19:chat@thread.v2"},
            {"replyChain": "1700000000001"},
            {"replyChain": {"id": 1700000000001}},
        ],
    )
    def test_rejects_values_of_the_wrong_type(self, channel_data):
        with pytest.raises(ValidationError):
            ChannelData.model_validate(channel_data)

    def test_is_available_on_an_activity(self):
        activity = MessageActivityInput(text="hi").with_channel_data(
            ChannelData(
                reply_chain=ReplyChainInfo(id="1700000000001"),
                chat=ChatInfo(id="19:user_bot@unq.gbl.spaces"),
            )
        )

        assert activity.channel_data is not None
        assert activity.channel_data.reply_chain is not None
        assert activity.channel_data.reply_chain.id == "1700000000001"
        assert activity.channel_data.chat is not None
        assert activity.channel_data.chat.id == "19:user_bot@unq.gbl.spaces"

    def test_serializes_with_camel_case_aliases(self):
        channel_data = ChannelData(
            chat=ChatInfo(id="19:chat@thread.v2", encrypted=EncryptedChatInfo(id="a:encrypted")),
            reply_chain=ReplyChainInfo(id="root-1"),
        )

        assert json.loads(channel_data.model_dump_json(exclude_none=True)) == {
            "chat": {"id": "19:chat@thread.v2", "encrypted": {"id": "a:encrypted"}},
            "replyChain": {"id": "root-1"},
        }
