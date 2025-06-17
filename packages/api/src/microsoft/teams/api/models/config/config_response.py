"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, Union

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel
from .config_auth import ConfigAuth


# Placeholder for external types
class CacheInfo(CustomBaseModel):
    """Placeholder for CacheInfo model from ../cache-info"""

    pass


class TaskModuleTask(CustomBaseModel):
    """Placeholder for TaskModuleResponse['task'] from ../task-module"""

    pass


class ConfigResponse(CustomBaseModel):
    """
    A container for the Config response payload
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    cache_info: Optional[CacheInfo] = None
    "The data of the ConfigResponse cache, including cache type and cache duration."

    # Placeholder - fix specification of task
    config: Union[ConfigAuth, TaskModuleTask]
    "The ConfigResponse config of BotConfigAuth or TaskModuleResponse"

    response_type: Literal["config"] = "config"
    "The type of response 'config'."
