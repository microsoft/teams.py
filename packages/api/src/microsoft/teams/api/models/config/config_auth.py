"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


# Placeholder for external type
class SuggestedActions(CustomBaseModel):
    """Placeholder for SuggestedActions model from ../suggested-actions"""

    pass


class ConfigAuth(CustomBaseModel):
    """
    The bot's authentication config for SuggestedActions
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    suggested_actions: Optional[SuggestedActions] = None
    "SuggestedActions for the Bot Config Auth"

    type: Literal["auth"] = "auth"
    "Type of the Bot Config Auth"
