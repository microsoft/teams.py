from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from .config_auth import ConfigAuth


# Placeholder for external types
class CacheInfo(BaseModel):
    """Placeholder for CacheInfo model from ../cache-info"""

    pass


class TaskModuleTask(BaseModel):
    """Placeholder for TaskModuleResponse['task'] from ../task-module"""

    pass


class ConfigResponse(BaseModel):
    """
    A container for the Config response payload
    """

    cache_info: Optional[CacheInfo] = Field(
        None,
        alias="cacheInfo",
        description="The data of the ConfigResponse cache, including cache type and cache duration.",
    )
    # Placeholder - fix specification of task
    config: Union[ConfigAuth, TaskModuleTask] = Field(
        ..., description="The ConfigResponse config of BotConfigAuth or TaskModuleResponse"
    )
    response_type: Literal["config"] = Field(
        "config", alias="responseType", description="The type of response 'config'."
    )
