"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.cards import IMBackAction
from microsoft_teams.cards.core import SubmitActionData as BaseSubmitActionData


def test_im_back_action_initialization():
    action = IMBackAction(value="Test Value")
    assert isinstance(action.data, BaseSubmitActionData)
    assert action.data.ms_teams is not None
    assert action.data.ms_teams["value"] == "Test Value"
