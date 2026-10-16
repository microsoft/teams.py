"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
from pathlib import Path
from typing import Type

import pytest
from microsoft_teams.api.activities.invoke.sign_in import SignInFailureInvokeActivity
from microsoft_teams.api.activities.invoke.suggested_action_submit import SuggestedActionSubmitInvokeActivity
from microsoft_teams.common.http import ClientOptions
from pydantic import BaseModel

# Map fixture filenames to their expected activity types
FIXTURE_ACTIVITY_MAP = {
    "signin_failure_invoke_activity.json": SignInFailureInvokeActivity,
    "suggested_action_submit_invoke_activity.json": SuggestedActionSubmitInvokeActivity,
}


@pytest.mark.parametrize("fixture_name", ["mock_http_client", "request_capture"])
async def test_mock_http_clients_ignore_environment_proxy(
    fixture_name: str, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    client = request.getfixturevalue(fixture_name)

    response = await client.get("/mock-only")

    assert response.status_code == 200
    assert response.json()["url"] == "https://mock.api.com/mock-only"


@pytest.mark.parametrize("share_http", [False, True])
async def test_request_capture_clones_preserve_mock_transport_with_proxy(
    share_http: bool, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    client = request.getfixturevalue("request_capture")
    clone = client.clone(ClientOptions(base_url="https://cloned.api.com"), share_http=share_http)
    nested_clone = clone.clone()

    response = await nested_clone.get("/mock-only")

    assert response.status_code == 200
    assert response.json()["url"] == "https://cloned.api.com/mock-only"
    assert len(client._capture.requests) == 1
    assert (clone.http is client.http) == share_http


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
