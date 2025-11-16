"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
from pathlib import Path
from typing import Type

import pytest
from microsoft.teams.api.activities.invoke.sign_in import SignInFailureInvokeActivity
from pydantic import BaseModel

# Map fixture filenames to their expected activity types
FIXTURE_ACTIVITY_MAP = {
    "signin_failure_invoke_activity.json": SignInFailureInvokeActivity,
}


@pytest.mark.unit
class TestFixtures:
    """Test deserialization of various activity fixtures."""

    @pytest.mark.parametrize(
        "fixture_filename,activity_type",
        [(fixture, activity_type) for fixture, activity_type in FIXTURE_ACTIVITY_MAP.items()],
        ids=lambda param: param if isinstance(param, str) else param.__name__,
    )
    def test_should_deserialize_activity_fixture(self, fixture_filename: str, activity_type: Type[BaseModel]) -> None:
        """Test deserializing activity from fixture file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_filename

        with open(fixture_path) as f:
            activity_dict = json.load(f)

        activity = activity_type.model_validate(activity_dict)

        # Verify basic activity properties
        assert activity.type == "invoke"
        assert hasattr(activity, "name")
