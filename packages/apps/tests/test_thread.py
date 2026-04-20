"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.apps.utils.thread import supports_threading, to_threaded_conversation_id


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


class TestSupportsThreading:
    def test_tacv2_returns_true(self):
        assert supports_threading("19:abc@thread.tacv2") is True

    def test_skype_returns_true(self):
        assert supports_threading("19:abc@thread.skype") is True

    def test_unq_gbl_spaces_returns_true(self):
        assert supports_threading("19:abc@unq.gbl.spaces") is True

    def test_thread_v2_returns_false(self):
        assert supports_threading("19:meeting_abc@thread.v2") is False

    def test_tacv2_with_messageid_suffix_returns_true(self):
        assert supports_threading("19:abc@thread.tacv2;messageid=123") is True

    def test_skype_with_messageid_suffix_returns_true(self):
        assert supports_threading("19:abc@thread.skype;messageid=456") is True

    def test_unq_gbl_spaces_with_messageid_suffix_returns_true(self):
        assert supports_threading("19:abc@unq.gbl.spaces;messageid=789") is True

    def test_thread_v2_with_messageid_suffix_returns_false(self):
        assert supports_threading("19:meeting_abc@thread.v2;messageid=111") is False
