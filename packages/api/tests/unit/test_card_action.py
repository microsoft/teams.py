"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.api.models.card.card_action import CardAction
from microsoft_teams.api.models.card.card_action_type import CardActionType


@pytest.mark.unit
class TestCardAction:
    """Unit tests for CardAction."""

    def test_deserialize_set_cache_policy_action(self) -> None:
        """Test setCachePolicy actions round-trip through validation and serialization."""
        action = CardAction.model_validate(
            {
                "type": "setCachePolicy",
                "title": "Open link",
                "value": {"type": "no-cache"},
            }
        )

        assert action.type is CardActionType.SET_CACHE_POLICY
        assert action.value == {"type": "no-cache"}

        data = action.model_dump(by_alias=True)

        assert data["type"] == "setCachePolicy"
        assert data["value"] == {"type": "no-cache"}
