from typing import Optional, Union

from ..custom_base_model import CustomBaseModel
from .messaging_extension_result import MessagingExtensionResult


# Placeholder for external types
class TaskModuleContinueResponse(CustomBaseModel):
    """Placeholder for TaskModuleContinueResponse from ../task-module"""

    pass


class TaskModuleMessageResponse(CustomBaseModel):
    """Placeholder for TaskModuleMessageResponse from ../task-module"""

    pass


class CacheInfo(CustomBaseModel):
    """Placeholder for CacheInfo from ../cache-info"""

    pass


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
