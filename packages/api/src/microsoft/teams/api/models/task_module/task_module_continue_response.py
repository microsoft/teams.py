"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from .task_module_response_base import TaskModuleResponseBase
from .task_module_task_info import TaskModuleTaskInfo


class TaskModuleContinueResponse(TaskModuleResponseBase):
    """Task Module Response with continue action."""

    type: Literal["continue"] = "continue"  #
    """Type of response, always 'continue' for this class."""

    value: Optional[TaskModuleTaskInfo] = None
    """The JSON for the Adaptive card to appear in the task module."""
