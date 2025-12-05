"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel
from ..suggested_actions import SuggestedActions


class ConfigAuth(CustomBaseModel):
    """
    The bot's authentication config for SuggestedActions
    """

    suggested_actions: Optional[SuggestedActions] = None
    "SuggestedActions for the Bot Config Auth"

    type: Literal["auth"] = "auth"
    "Type of the Bot Config Auth"
