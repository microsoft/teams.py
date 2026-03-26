"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from microsoft_teams.api.activities.message import MessageActivity
from microsoft_teams.api.models import Account, ConversationAccount, MentionEntity
from microsoft_teams.api.models.entity import QuotedReplyData, QuotedReplyEntity


class TestMessageActivityQuotedReplies:
    """Tests for the get_quoted_messages property on MessageActivity"""

    def _create_message_activity(self, text: str = "Hello") -> MessageActivity:
        """Create a basic MessageActivity for testing"""
        return MessageActivity(
            id="msg-123",
            text=text,
            from_=Account(id="user-1", name="User"),
            conversation=ConversationAccount(id="conv-1", conversation_type="personal"),
            recipient=Account(id="bot-1", name="Bot"),
        )

    def test_get_quoted_messages_returns_empty_when_no_entities(self):
        """Test that get_quoted_messages returns empty list when no entities exist"""
        activity = self._create_message_activity()
        assert activity.entities is None
        assert activity.get_quoted_messages() == []

    def test_get_quoted_messages_returns_empty_when_no_quoted_reply_entities(self):
        """Test that get_quoted_messages returns empty list when entities exist but none are QuotedReplyEntity"""
        activity = self._create_message_activity()
        activity.entities = [
            MentionEntity(mentioned=Account(id="user-1", name="User"), text="<at>User</at>"),
        ]
        assert activity.get_quoted_messages() == []

    def test_get_quoted_messages_returns_matching_entities(self):
        """Test that get_quoted_messages filters and returns only QuotedReplyEntity instances"""
        activity = self._create_message_activity()
        quoted = QuotedReplyEntity(quoted_reply=QuotedReplyData(message_id="msg-456"))
        activity.entities = [
            MentionEntity(mentioned=Account(id="user-1", name="User"), text="<at>User</at>"),
            quoted,
        ]
        result = activity.get_quoted_messages()
        assert len(result) == 1
        assert result[0] is quoted
        assert result[0].quoted_reply.message_id == "msg-456"

    def test_get_quoted_messages_returns_multiple(self):
        """Test that get_quoted_messages returns multiple QuotedReplyEntity instances"""
        activity = self._create_message_activity()
        q1 = QuotedReplyEntity(quoted_reply=QuotedReplyData(message_id="msg-1"))
        q2 = QuotedReplyEntity(quoted_reply=QuotedReplyData(message_id="msg-2"))
        activity.entities = [q1, q2]
        result = activity.get_quoted_messages()
        assert len(result) == 2
        assert result[0].quoted_reply.message_id == "msg-1"
        assert result[1].quoted_reply.message_id == "msg-2"


class TestMessageActivityInputAddQuotedReply:
    """Tests for the add_quote builder method on MessageActivityInput"""

    def test_add_quote_adds_entity_and_placeholder(self):
        from microsoft_teams.api.activities.message import MessageActivityInput

        msg = MessageActivityInput().add_quote("msg-1")
        assert len(msg.entities) == 1
        assert msg.entities[0].type == "quotedReply"
        assert msg.entities[0].quoted_reply.message_id == "msg-1"
        assert msg.text == '<quoted messageId="msg-1"/>'

    def test_add_quote_with_response(self):
        from microsoft_teams.api.activities.message import MessageActivityInput

        msg = MessageActivityInput().add_quote("msg-1", "my response")
        assert msg.text == '<quoted messageId="msg-1"/> my response'

    def test_add_quote_multi_quote_interleaved(self):
        from microsoft_teams.api.activities.message import MessageActivityInput

        msg = (
            MessageActivityInput()
            .add_quote("msg-1", "response to first")
            .add_quote("msg-2", "response to second")
        )
        assert msg.text == '<quoted messageId="msg-1"/> response to first<quoted messageId="msg-2"/> response to second'
        assert len(msg.entities) == 2

    def test_add_quote_grouped(self):
        from microsoft_teams.api.activities.message import MessageActivityInput

        msg = MessageActivityInput().add_quote("msg-1").add_quote("msg-2", "response to both")
        assert msg.text == '<quoted messageId="msg-1"/><quoted messageId="msg-2"/> response to both'

    def test_add_quote_chainable_with_add_text(self):
        from microsoft_teams.api.activities.message import MessageActivityInput

        msg = MessageActivityInput().add_quote("msg-1").add_text(" manual text")
        assert msg.text == '<quoted messageId="msg-1"/> manual text'
