"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .task_fetch import TaskFetchInvokeActivity
from .task_submit import TaskSubmitInvokeActivity

TaskInvokeActivity = Annotated[
    Union[TaskFetchInvokeActivity, TaskSubmitInvokeActivity],
    Field(discriminator="name"),
]

__all__ = [
    "TaskFetchInvokeActivity",
    "TaskSubmitInvokeActivity",
    "TaskInvokeActivity",
]
