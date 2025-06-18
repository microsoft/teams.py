"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ..custom_base_model import CustomBaseModel


class MessagingExtensionParameter(CustomBaseModel):
    """
    Messaging extension query parameters
    """

    name: Optional[str] = None
    "Name of the parameter"

    value: Optional[Any] = None
    "Value of the parameter"
