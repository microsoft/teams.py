"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
from pathlib import Path

import pytest
from microsoft.teams.api.activities.invoke.sign_in import SignInFailureInvokeActivity


@pytest.mark.unit
class TestFixtures:
    """Test deserialization of various activity fixtures."""

    def test_should_deserialize_signin_failure_activity_fixture(self) -> None:
        """Test deserializing a signin failure activity from fixture file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "signin_failure_invoke_activity.json"

        with open(fixture_path) as f:
            activity_dict = json.load(f)

        activity = SignInFailureInvokeActivity.model_validate(activity_dict)

        assert activity.name == "signin/failure"
        assert activity.type == "invoke"
        assert activity.value.code == "resourcematchfailed"
        assert activity.value.message == "Resource match failed"
