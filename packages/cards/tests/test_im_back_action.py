"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.cards import IMBackAction, SubmitActionData


def test_im_back_action_initialization():
    action = IMBackAction(value="Test Value")
    assert isinstance(action.data, SubmitActionData)
    assert action.data.ms_teams is not None
    assert action.data.ms_teams["value"] == "Test Value"
