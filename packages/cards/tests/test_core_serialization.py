"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
from typing import Any, cast

from microsoft.teams.cards import (
    ActionSet,
    AdaptiveCard,
    ExecuteAction,
    SubmitAction,
    SubmitActionData,
    TeamsCardProperties,
    TextBlock,
    ToggleInput,
)


def test_adaptive_card_serialization():
    """Test AdaptiveCard with nested elements serializes without empty objects."""
    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="Hello world", wrap=True, weight="Bolder"),
            ToggleInput(label="Notify me", id="notify"),
            ActionSet(
                actions=[
                    ExecuteAction(title="Submit")
                    .with_data(SubmitActionData(ms_teams={"action": "submit_basic"}))
                    .with_associated_inputs("auto")
                ]
            ),
        ],
    )

    # Test serialization
    json_str = card.model_dump_json(exclude_none=True)
    parsed = json.loads(json_str)

    # Verify no empty objects in body array
    assert len(parsed["body"]) == 3
    for item in parsed["body"]:
        assert item != {}
        assert "type" in item

    # Verify nested action is not empty
    action_set = parsed["body"][2]
    assert action_set["type"] == "ActionSet"
    assert action_set["actions"][0] != {}
    assert action_set["actions"][0]["type"] == "Action.Execute"


def test_action_set_serialization():
    """Test ActionSet with multiple actions serializes correctly."""
    action_set = ActionSet(
        actions=[
            ExecuteAction(title="Execute").with_data(SubmitActionData(ms_teams={"action": "execute"})),
            SubmitAction(title="Submit").with_data(SubmitActionData(ms_teams={"action": "submit"})),
        ]
    )

    json_str = action_set.model_dump_json(exclude_none=True)
    parsed = json.loads(json_str)

    # Verify no empty actions
    assert len(parsed["actions"]) == 2
    for action in parsed["actions"]:
        assert action != {}
        assert "type" in action


def test_adaptive_card_deserialization():
    """Test creating AdaptiveCard from JSON using model_validate."""
    card_data = {
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Select the examples you want to see!",
                "size": "Large",
                "weight": "Bolder",
            }
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Simple form test",
                "data": {"msteams": {"type": "task/fetch"}, "opendialogtype": "simple_form"},
            }
        ],
    }

    # Create card from JSON
    card = AdaptiveCard.model_validate(card_data)

    # Verify deserialization
    assert card.type == "AdaptiveCard"
    assert card.version == "1.4"
    assert card.body is not None and len(card.body) == 1
    assert card.actions is not None and len(card.actions) == 1

    # Verify elements - cast to access attributes
    text_block = cast(TextBlock, card.body[0])
    assert text_block.type == "TextBlock"
    assert text_block.text == "Select the examples you want to see!"

    action = cast(SubmitAction, card.actions[0])
    assert action.type == "Action.Submit"
    assert action.title == "Simple form test"


def test_serialization_round_trip():
    """Test serialize -> deserialize -> serialize maintains structure."""
    original_card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[TextBlock(text="Test text"), ActionSet(actions=[ExecuteAction(title="Test action")])],
    )

    # Serialize to JSON
    json_str = original_card.model_dump_json(exclude_none=True)

    # Deserialize from JSON
    card_data = json.loads(json_str)
    reconstructed_card = AdaptiveCard.model_validate(card_data)

    # Serialize again
    json_str2 = reconstructed_card.model_dump_json(exclude_none=True)
    parsed2 = json.loads(json_str2)

    # Verify no empty objects after round-trip
    assert parsed2["body"][0] != {}
    assert parsed2["body"][1]["actions"][0] != {}


def test_alias_serialization():
    """Test camelCase alias conversion with SerializeAsAny."""
    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json", body=[TextBlock(text="Test", is_visible=True)]
    )

    json_str = card.model_dump_json(exclude_none=True, by_alias=True)
    parsed = json.loads(json_str)

    # Verify alias conversion
    assert "schema" in parsed  # ac_schema -> schema
    text_block = parsed["body"][0]
    assert "isVisible" in text_block  # is_visible -> isVisible


def test_single_object_fallback_serialization():
    """Test if single object fallback properties serialize correctly."""
    # Create an ExecuteAction with a fallback that's another Action
    execute_action = ExecuteAction(title="Primary Action")
    fallback_action = SubmitAction(title="Fallback Submit")
    execute_action.fallback = fallback_action

    json_str = execute_action.model_dump_json(exclude_none=True)
    parsed = json.loads(json_str)

    # Check that fallback is present and serialized correctly (not as empty object)
    assert "fallback" in parsed, "Fallback property should be present in serialized JSON"
    assert parsed["fallback"] != {}, "Fallback should not be an empty object"
    assert "type" in parsed["fallback"], "Fallback should have a type field"
    assert parsed["fallback"]["type"] == "Action.Submit"
    assert parsed["fallback"]["title"] == "Fallback Submit"


def test_ms_teams_serializes_to_msteams():
    """Test that ms_teams field serializes to 'msteams' instead of 'msTeams'."""
    # Test AdaptiveCard.ms_teams serialization
    card = AdaptiveCard(version="1.5", body=[])
    card.ms_teams = TeamsCardProperties(width="full")

    json_str = card.model_dump_json(exclude_none=True, by_alias=True)
    parsed = json.loads(json_str)

    # Verify ms_teams serializes to 'msteams' not 'msTeams'
    assert "msteams" in parsed, "ms_teams should serialize to 'msteams'"
    assert "msTeams" not in parsed, "ms_teams should not serialize to 'msTeams'"
    assert parsed["msteams"]["width"] == "full"

    # Test deserialization from 'msteams'
    card_data: dict[str, Any] = {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [],
        "msteams": {"width": "full"},
    }
    card = AdaptiveCard.model_validate(card_data)
    assert card.ms_teams is not None
    assert card.ms_teams.width == "full"
