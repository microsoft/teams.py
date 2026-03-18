"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from microsoft_teams.api.models.entity import QuotedReplyData, QuotedReplyEntity


class TestQuotedReplyData:
    """Tests for QuotedReplyData model"""

    def test_minimal_creation(self):
        """Test creating QuotedReplyData with only required fields"""
        data = QuotedReplyData(message_id="msg-123")
        assert data.message_id == "msg-123"
        assert data.sender_id is None
        assert data.sender_name is None
        assert data.preview is None
        assert data.time is None
        assert data.is_reply_deleted is None
        assert data.validated_message_reference is None

    def test_full_creation(self):
        """Test creating QuotedReplyData with all fields"""
        data = QuotedReplyData(
            message_id="msg-123",
            sender_id="user-456",
            sender_name="Test User",
            preview="Hello world",
            time="2024-01-01T12:00:00Z",
            is_reply_deleted=False,
            validated_message_reference=True,
        )
        assert data.message_id == "msg-123"
        assert data.sender_id == "user-456"
        assert data.sender_name == "Test User"
        assert data.preview == "Hello world"
        assert data.time == "2024-01-01T12:00:00Z"
        assert data.is_reply_deleted is False
        assert data.validated_message_reference is True

    def test_serialization_camel_case(self):
        """Test that QuotedReplyData serializes to camelCase"""
        data = QuotedReplyData(
            message_id="msg-123",
            sender_id="user-456",
            sender_name="Test User",
            is_reply_deleted=False,
            validated_message_reference=True,
        )
        serialized = data.model_dump(by_alias=True, exclude_none=True)
        assert "messageId" in serialized
        assert "senderId" in serialized
        assert "senderName" in serialized
        assert "isReplyDeleted" in serialized
        assert "validatedMessageReference" in serialized
        # Ensure snake_case keys are NOT present
        assert "message_id" not in serialized
        assert "sender_id" not in serialized

    def test_deserialization_from_camel_case(self):
        """Test that QuotedReplyData deserializes from camelCase"""
        data = QuotedReplyData.model_validate({
            "messageId": "msg-123",
            "senderId": "user-456",
            "senderName": "Test User",
            "preview": "Hello world",
            "time": "2024-01-01T12:00:00Z",
            "isReplyDeleted": False,
            "validatedMessageReference": True,
        })
        assert data.message_id == "msg-123"
        assert data.sender_id == "user-456"
        assert data.sender_name == "Test User"
        assert data.preview == "Hello world"
        assert data.is_reply_deleted is False
        assert data.validated_message_reference is True


class TestQuotedReplyEntity:
    """Tests for QuotedReplyEntity model"""

    def test_creation_with_defaults(self):
        """Test creating QuotedReplyEntity with default type"""
        entity = QuotedReplyEntity(
            quoted_reply=QuotedReplyData(message_id="msg-123")
        )
        assert entity.type == "quotedReply"
        assert entity.quoted_reply.message_id == "msg-123"

    def test_serialization_camel_case(self):
        """Test that QuotedReplyEntity serializes to camelCase"""
        entity = QuotedReplyEntity(
            quoted_reply=QuotedReplyData(message_id="msg-123", sender_name="Alice")
        )
        serialized = entity.model_dump(by_alias=True, exclude_none=True)
        assert serialized["type"] == "quotedReply"
        assert "quotedReply" in serialized
        assert serialized["quotedReply"]["messageId"] == "msg-123"
        assert serialized["quotedReply"]["senderName"] == "Alice"

    def test_deserialization_from_camel_case(self):
        """Test that QuotedReplyEntity deserializes from camelCase"""
        entity = QuotedReplyEntity.model_validate({
            "type": "quotedReply",
            "quotedReply": {
                "messageId": "msg-123",
                "senderId": "user-456",
                "senderName": "Test User",
            },
        })
        assert entity.type == "quotedReply"
        assert entity.quoted_reply.message_id == "msg-123"
        assert entity.quoted_reply.sender_id == "user-456"
        assert entity.quoted_reply.sender_name == "Test User"

    def test_round_trip_serialization(self):
        """Test that serialization and deserialization are consistent"""
        original = QuotedReplyEntity(
            quoted_reply=QuotedReplyData(
                message_id="msg-123",
                sender_id="user-456",
                sender_name="Test User",
                preview="Hello world",
                time="2024-01-01T12:00:00Z",
                is_reply_deleted=False,
                validated_message_reference=True,
            )
        )
        serialized = original.model_dump(by_alias=True)
        deserialized = QuotedReplyEntity.model_validate(serialized)
        assert deserialized.type == original.type
        assert deserialized.quoted_reply.message_id == original.quoted_reply.message_id
        assert deserialized.quoted_reply.sender_id == original.quoted_reply.sender_id
        assert deserialized.quoted_reply.sender_name == original.quoted_reply.sender_name
        assert deserialized.quoted_reply.preview == original.quoted_reply.preview
        assert deserialized.quoted_reply.time == original.quoted_reply.time
        assert deserialized.quoted_reply.is_reply_deleted == original.quoted_reply.is_reply_deleted
        assert deserialized.quoted_reply.validated_message_reference == original.quoted_reply.validated_message_reference
