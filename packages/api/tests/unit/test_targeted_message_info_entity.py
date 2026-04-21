"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import pytest
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
