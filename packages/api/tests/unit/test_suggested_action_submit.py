"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import warnings
from pathlib import Path

import pytest
from microsoft_teams.api.activities import ActivityTypeAdapter
from microsoft_teams.api.activities.invoke.suggested_action_submit import SuggestedActionSubmitInvokeActivity
from microsoft_teams.api.models.card.card_action import CardAction
from microsoft_teams.api.models.card.card_action_type import CardActionType
from microsoft_teams.api.models.suggested_actions import SuggestedActions
from microsoft_teams.common.experimental import ExperimentalWarning


@pytest.fixture
def fixture_json() -> dict:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "suggested_action_submit_invoke_activity.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.mark.unit
class TestSuggestedActionSubmitInvokeActivity:
    """Unit tests for SuggestedActionSubmitInvokeActivity."""

    def test_deserialize_directly(self, fixture_json: dict) -> None:
        """Test deserializing directly into SuggestedActionSubmitInvokeActivity."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ExperimentalWarning)
            activity = SuggestedActionSubmitInvokeActivity.model_validate(fixture_json)

        assert activity.id == "suggestedActionSubmitId"
        assert activity.channel_id == "channelId"
        assert activity.name == "suggestedActions/submit"
        assert activity.value == {"vote": "approve"}

    def test_deserialize_dispatched_from_activity_base(self, fixture_json: dict) -> None:
        """Test that the activity is dispatched correctly from the Activity discriminated union."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ExperimentalWarning)
            activity = ActivityTypeAdapter.validate_python(fixture_json)

        assert isinstance(activity, SuggestedActionSubmitInvokeActivity)
        assert activity.name == "suggestedActions/submit"
        assert activity.value == {"vote": "approve"}

    def test_outgoing_message_with_action_submit_suggested_action(self) -> None:
        """Test that a message with Action.Submit suggested actions serializes correctly."""
        actions = [
            CardAction(type=CardActionType.SUBMIT, title="Approve", value={"vote": "approve"}),
            CardAction(type=CardActionType.SUBMIT, title="Reject", value={"vote": "reject"}),
        ]
        suggested_actions = SuggestedActions(to=[], actions=actions)

        data = suggested_actions.model_dump(by_alias=True)

        assert data["actions"][0]["type"] == "Action.Submit"
        assert data["actions"][0]["title"] == "Approve"
        assert data["actions"][0]["value"] == {"vote": "approve"}
        assert data["actions"][1]["type"] == "Action.Submit"
        assert data["actions"][1]["title"] == "Reject"
        assert data["actions"][1]["value"] == {"vote": "reject"}

    def test_experimental_warning_emitted(self, fixture_json: dict) -> None:
        """Test that the class is marked experimental."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            SuggestedActionSubmitInvokeActivity(
                id="test",
                from_={"id": "u1", "name": "U"},
                conversation={"id": "c1"},
                recipient={"id": "b1", "name": "B"},
                value={"vote": "approve"},
            )

        experimental_warnings = [x for x in w if issubclass(x.category, ExperimentalWarning)]
        assert len(experimental_warnings) == 1
        assert "ExperimentalTeamsSuggestedAction" in str(experimental_warnings[0].message)
