"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
from microsoft_teams.api import MessageActivityInput
from microsoft_teams.api.models.entity.targeted_message_info_entity import TargetedMessageInfoEntity


@pytest.mark.unit
class TestTargetedMessageInfoEntity:
    """Unit tests for TargetedMessageInfoEntity."""

    def test_default_type(self) -> None:
        entity = TargetedMessageInfoEntity(message_id="1772129782775")
        assert entity.type == "targetedMessageInfo"

    def test_message_id(self) -> None:
        entity = TargetedMessageInfoEntity(message_id="1772129782775")
        assert entity.message_id == "1772129782775"

    def test_serialization_camel_case(self) -> None:
        entity = TargetedMessageInfoEntity(message_id="1772129782775")
        data = entity.model_dump(by_alias=True, exclude_none=True)
        assert data == {
            "type": "targetedMessageInfo",
            "messageId": "1772129782775",
        }

    def test_deserialization_camel_case(self) -> None:
        entity = TargetedMessageInfoEntity.model_validate(
            {
                "type": "targetedMessageInfo",
                "messageId": "1772129782775",
            }
        )
        assert entity.type == "targetedMessageInfo"
        assert entity.message_id == "1772129782775"


@pytest.mark.unit
class TestAddTargetedMessageInfo:
    """Tests for MessageActivityInput.add_targeted_message_info including QR collision guard."""

    def test_adds_entity(self) -> None:
        activity = MessageActivityInput(text="test")
        activity.add_targeted_message_info("12345")

        targeted = [e for e in (activity.entities or []) if isinstance(e, TargetedMessageInfoEntity)]
        assert len(targeted) == 1
        assert targeted[0].message_id == "12345"

    def test_does_not_duplicate_when_entity_exists(self) -> None:
        activity = MessageActivityInput(text="test")
        activity.add_entity(TargetedMessageInfoEntity(message_id="9999"))
        activity.add_targeted_message_info("12345")

        targeted = [e for e in (activity.entities or []) if isinstance(e, TargetedMessageInfoEntity)]
        assert len(targeted) == 1
        assert targeted[0].message_id == "9999"

    def test_strips_qr_even_when_entity_already_exists(self) -> None:
        """When developer pre-attaches targetedMessageInfo and reply() adds quotedReply,
        add_targeted_message_info should still strip the quotedReply artifacts."""
        from unittest.mock import MagicMock

        qr_entity = MagicMock()
        qr_entity.type = "quotedReply"

        activity = MessageActivityInput(text='<quoted messageId="12345"/> Here is my reply')
        activity.add_entity(TargetedMessageInfoEntity(message_id="9999"))
        activity.entities.append(qr_entity)  # type: ignore[arg-type]

        activity.add_targeted_message_info("12345")

        # Should not duplicate the entity
        targeted = [e for e in (activity.entities or []) if isinstance(e, TargetedMessageInfoEntity)]
        assert len(targeted) == 1
        assert targeted[0].message_id == "9999"
        # Should still strip quotedReply
        assert not any(getattr(e, "type", None) == "quotedReply" for e in (activity.entities or []))
        assert activity.text == "Here is my reply"

    def test_strips_quoted_reply_entities(self) -> None:
        activity = MessageActivityInput(text="test", entities=[])
        # Simulate a quotedReply entity (generic entity with type="quotedReply")

        # Use a mock-like approach: create a simple object with type="quotedReply"
        from unittest.mock import MagicMock

        qr_entity = MagicMock()
        qr_entity.type = "quotedReply"
        activity.entities = [qr_entity]  # type: ignore[list-item]

        activity.add_targeted_message_info("12345")

        assert not any(getattr(e, "type", None) == "quotedReply" for e in (activity.entities or []))
        targeted = [e for e in (activity.entities or []) if isinstance(e, TargetedMessageInfoEntity)]
        assert len(targeted) == 1

    def test_strips_quoted_placeholder_from_text(self) -> None:
        activity = MessageActivityInput(text='<quoted messageId="12345"/> Here is my reply')
        activity.add_targeted_message_info("12345")

        assert activity.text == "Here is my reply"
        targeted = [e for e in (activity.entities or []) if isinstance(e, TargetedMessageInfoEntity)]
        assert len(targeted) == 1
