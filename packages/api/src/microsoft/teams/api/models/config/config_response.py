"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, Union

from ..cache_info import CacheInfo
from ..custom_base_model import CustomBaseModel
from ..task_module.task_module_continue_response import TaskModuleContinueResponse
from ..task_module.task_module_message_response import TaskModuleMessageResponse
from .config_auth import ConfigAuth


class ConfigResponse(CustomBaseModel):
    """
    A container for the Config response payload
    """

    cache_info: Optional[CacheInfo] = None
    "The data of the ConfigResponse cache, including cache type and cache duration."

    config: Union[ConfigAuth, Union[TaskModuleContinueResponse, TaskModuleMessageResponse]]
    "The ConfigResponse config of BotConfigAuth or TaskModuleResponse"

    response_type: Literal["config"] = "config"
    "The type of response 'config'."
