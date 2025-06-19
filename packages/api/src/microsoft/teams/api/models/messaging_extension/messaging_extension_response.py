"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..cache_info import CacheInfo
from ..custom_base_model import CustomBaseModel
from .messaging_extension_result import MessagingExtensionResult


class MessagingExtensionResponse(CustomBaseModel):
    """
    An interface representing MessagingExtensionResponse.
    Messaging extension response
    """

    compose_extension: Optional[MessagingExtensionResult] = None
    "Compose extension response"

    cache_info: Optional[CacheInfo] = None
    "Cache information for the response"
