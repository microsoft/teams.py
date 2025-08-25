"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from ..core import SubmitAction, SubmitActionData, TaskFetchSubmitActionData


class TaskFetchAction(SubmitAction):
    def __init__(self, value: Dict[str, Any]):
        super().__init__()
        action_data = TaskFetchSubmitActionData().with_value(value)
        self.data = SubmitActionData(ms_teams=action_data.model_dump())
