"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .task_fetch import TaskFetchInvokeActivity
from .task_submit import TaskSubmitInvokeActivity

TaskInvokeActivity = Union[TaskFetchInvokeActivity, TaskSubmitInvokeActivity]

__all__ = [
    "TaskFetchInvokeActivity",
    "TaskSubmitInvokeActivity",
    "TaskInvokeActivity",
]
