"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings
from typing import Any, Dict

from ..core import SubmitAction, SubmitActionData, TaskFetchSubmitActionData


class TaskFetchAction(SubmitAction):
    """This class is deprecated. Please use TaskFetchSubmitActionData instead.
    This will be removed in a future version of the SDK."""

    def __init__(self, value: Dict[str, Any]):
        warnings.warn(
            "TaskFetchAction is deprecated. Use TaskFetchSubmitActionData instead. "
            "This will be removed in a future version of the SDK.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()
        # For task/fetch, the action data actually goes in the SubmitActionData, not with
        # msteams. msteams simply contains { type: 'task/fetch' }
        self.data = SubmitActionData(**value).with_ms_teams(TaskFetchSubmitActionData().model_dump())
