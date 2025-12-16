"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from ..cache_info import CacheInfo
from ..custom_base_model import CustomBaseModel
from .task_module_continue_response import TaskModuleContinueResponse
from .task_module_message_response import TaskModuleMessageResponse


class TaskModuleResponse(CustomBaseModel):
    """Envelope for Task Module Response."""

    task: Optional[Union[TaskModuleContinueResponse, TaskModuleMessageResponse]] = None
    """The JSON for the response to appear in the task module."""

    cache_info: Optional[CacheInfo] = None
    """The cache info for this response."""
