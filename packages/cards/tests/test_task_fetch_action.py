"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.cards import SubmitActionData, TaskFetchAction


def test_invoke_action_initialization():
    action = TaskFetchAction({"test": "Test Value"})
    assert isinstance(action.data, SubmitActionData)
    assert action.data.ms_teams is not None
    # ms_teams should contain the task/fetch type
    assert action.data.ms_teams["type"] == "task/fetch"
    # The actual data goes at the root of SubmitActionData
    assert action.data.model_dump()["test"] == "Test Value"
