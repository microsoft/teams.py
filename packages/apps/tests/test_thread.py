"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.api import Account, ConversationAccount, MessageActivity
from microsoft_teams.api.models.channel_data import ChannelData, ThreadInfo
from microsoft_teams.apps.utils import get_default_thread_id, get_proactive_thread_reference
from microsoft_teams.apps.utils.thread import to_threaded_conversation_id


class TestToThreadedConversationId:
    def test_constructs_threaded_conversation_id(self):
        result = to_threaded_conversation_id("19:abc@thread.skype", "1680000000000")
        assert result == "19:abc@thread.skype;messageid=1680000000000"

    def test_works_with_different_conversation_id_formats(self):
        result = to_threaded_conversation_id("19:meeting_abc@thread.v2", "999")
        assert result == "19:meeting_abc@thread.v2;messageid=999"

    def test_raises_on_empty_conversation_id(self):
        with pytest.raises(ValueError, match="conversation_id must be a non-empty string"):
            to_threaded_conversation_id("", "123")

    def test_raises_on_empty_message_id(self):
        with pytest.raises(ValueError, match="Invalid message_id"):
            to_threaded_conversation_id("19:abc@thread.skype", "")

    def test_raises_on_zero_message_id(self):
        with pytest.raises(ValueError, match="Invalid message_id"):
            to_threaded_conversation_id("19:abc@thread.skype", "0")

    def test_raises_on_non_numeric_message_id(self):
        with pytest.raises(ValueError, match="Invalid message_id"):
            to_threaded_conversation_id("19:abc@thread.skype", "abc")

    def test_raises_on_negative_message_id(self):
        with pytest.raises(ValueError, match="Invalid message_id"):
            to_threaded_conversation_id("19:abc@thread.skype", "-1")

    def test_raises_on_decimal_message_id(self):
        with pytest.raises(ValueError, match="Invalid message_id"):
            to_threaded_conversation_id("19:abc@thread.skype", "1.5")

    def test_strips_existing_messageid_and_replaces_with_thread_root(self):
        result = to_threaded_conversation_id("19:abc@thread.skype;messageid=111", "222")
        assert result == "19:abc@thread.skype;messageid=222"


class TestGetThreadReference:
    @staticmethod
    def _activity(conversation_id: str, *, thread_id: str | None = None) -> MessageActivity:
        return MessageActivity(
            id="inbound-id",
            from_=Account(id="user-id"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id=conversation_id),
            channel_data=ChannelData(thread=ThreadInfo(id=thread_id)) if thread_id else None,
        )

    def test_prefers_typed_thread_metadata(self):
        activity = self._activity("19:abc@thread.skype;messageid=123", thread_id="typed-root")

        assert get_proactive_thread_reference(activity) == ("19:abc@thread.skype", "typed-root")

    def test_uses_legacy_thread_suffix(self):
        activity = self._activity("19:abc@thread.skype;messageid=123")

        assert get_proactive_thread_reference(activity) == ("19:abc@thread.skype", "123")

    def test_uses_activity_id_for_root_message(self):
        activity = self._activity("19:abc@thread.skype")

        assert get_proactive_thread_reference(activity) == ("19:abc@thread.skype", "inbound-id")


class TestGetCurrentThreadRootId(TestGetThreadReference):
    def test_uses_typed_thread_metadata(self):
        activity = self._activity("19:abc@thread.skype", thread_id="typed-root")

        assert get_default_thread_id(activity) == "typed-root"

    def test_uses_legacy_thread_suffix(self):
        activity = self._activity("19:abc@thread.skype;messageid=123")

        assert get_default_thread_id(activity) == "123"

    def test_uses_activity_id_for_channel_root(self):
        activity = self._activity("19:abc@thread.skype")
        activity.conversation.conversation_type = "channel"

        assert get_default_thread_id(activity) == "inbound-id"

    def test_returns_none_for_group_chat_root(self):
        activity = self._activity("19:abc@thread.skype")
        activity.conversation.conversation_type = "groupChat"

        assert get_default_thread_id(activity) is None
