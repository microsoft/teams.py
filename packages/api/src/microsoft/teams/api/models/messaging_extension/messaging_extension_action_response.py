"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from ..cache_info import CacheInfo
from ..custom_base_model import CustomBaseModel
from ..task_module import TaskModuleContinueResponse, TaskModuleMessageResponse
from .messaging_extension_result import MessagingExtensionResult


class MessagingExtensionActionResponse(CustomBaseModel):
    """
    Response of messaging extension action
    """

    task: Optional[Union[TaskModuleContinueResponse, TaskModuleMessageResponse]] = None
    "The JSON for the response to appear in the task module."

    compose_extension: Optional[MessagingExtensionResult] = None
    "The messaging extension result"

    cache_info: Optional[CacheInfo] = None
    "The cache info for this response"
