"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft.teams.api.activities.invoke.sign_in import SignInFailureInvokeActivity
from microsoft.teams.api.models import Account, ConversationAccount, SignInFailure


@pytest.mark.unit
class TestSignInFailureInvokeActivity:
    """Unit tests for SignInFailureInvokeActivity class."""

    def test_should_create_signin_failure_activity(self) -> None:
        """Test creating a signin failure activity with code and message."""
        failure = SignInFailure(code="resourcematchfailed", message="Resource match failed")
        user = Account(id="user-1", name="Test User")
        bot = Account(id="bot-1", name="Test Bot")
        conversation = ConversationAccount(id="conv-1")

        activity = SignInFailureInvokeActivity(
            id="activity-1",
            name="signin/failure",
            value=failure,
            from_=user,
            conversation=conversation,
            recipient=bot,
        )

        assert activity.name == "signin/failure"
        assert activity.type == "invoke"
        assert activity.value.code == "resourcematchfailed"
        assert activity.value.message == "Resource match failed"

    def test_should_deserialize_signin_failure_activity(self) -> None:
        """Test deserializing a signin failure activity from JSON-like dict."""
        activity_dict = {
            "id": "activity-1",
            "name": "signin/failure",
            "type": "invoke",
            "from": {"id": "user-1", "name": "Test User"},
            "conversation": {"id": "conv-1"},
            "recipient": {"id": "bot-1", "name": "Test Bot"},
            "value": {"code": "resourcematchfailed", "message": "Resource match failed"},
        }

        activity = SignInFailureInvokeActivity.model_validate(activity_dict)

        assert activity.name == "signin/failure"
        assert activity.type == "invoke"
        assert activity.value.code == "resourcematchfailed"
        assert activity.value.message == "Resource match failed"

    def test_should_serialize_signin_failure_activity(self) -> None:
        """Test serializing a signin failure activity to dict."""
        failure = SignInFailure(code="unauthorized", message="Unauthorized access")
        user = Account(id="user-1", name="Test User")
        bot = Account(id="bot-1", name="Test Bot")
        conversation = ConversationAccount(id="conv-1")

        activity = SignInFailureInvokeActivity(
            id="activity-1",
            name="signin/failure",
            value=failure,
            from_=user,
            conversation=conversation,
            recipient=bot,
        )

        serialized = activity.model_dump()

        assert serialized["name"] == "signin/failure"
        assert serialized["type"] == "invoke"
        assert serialized["value"]["code"] == "unauthorized"
        assert serialized["value"]["message"] == "Unauthorized access"
