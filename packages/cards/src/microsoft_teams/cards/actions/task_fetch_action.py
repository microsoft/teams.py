"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from ..core import SubmitAction, SubmitActionData, TaskFetchSubmitActionData


class TaskFetchAction(SubmitAction):
    def __init__(self, value: Dict[str, Any]):
        super().__init__()
        # For task/fetch, the action data actually goes in the SubmitActionData, not with
        # msteams. msteams simply contains { type: 'task/fetch' }
        self.data = SubmitActionData(**value).with_ms_teams(TaskFetchSubmitActionData().model_dump())
