"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.cards import SignInAction, SubmitActionData


def test_sign_in_action_initialization():
    action = SignInAction(value="Test Value")
    assert isinstance(action.data, SubmitActionData)
    assert action.data.ms_teams is not None
    assert action.data.ms_teams["value"] == "Test Value"
