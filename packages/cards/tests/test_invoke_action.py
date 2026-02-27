"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.cards import InvokeAction
from microsoft_teams.cards.core import SubmitActionData as BaseSubmitActionData


def test_invoke_action_initialization():
    action = InvokeAction({"test": "Test Value"})
    assert isinstance(action.data, BaseSubmitActionData)
    assert action.data.ms_teams is not None
    assert action.data.ms_teams["value"]["test"] == "Test Value"
