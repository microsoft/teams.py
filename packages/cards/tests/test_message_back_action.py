"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.cards import MessageBackAction
from microsoft_teams.cards.core import SubmitActionData as BaseSubmitActionData


def test_message_back_action_initialization():
    action = MessageBackAction(text="Message Back Test", value="Test Value", display_text="Test Text")
    assert isinstance(action.data, BaseSubmitActionData)
    assert action.data.ms_teams is not None
    assert action.data.ms_teams["value"] == "Test Value"
    assert action.data.ms_teams["text"] == "Message Back Test"
    assert action.data.ms_teams["displayText"] == "Test Text"
