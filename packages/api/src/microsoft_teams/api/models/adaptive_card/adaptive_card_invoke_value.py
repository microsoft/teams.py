"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel
from .adaptive_card_authentication import AdaptiveCardAuthentication
from .adaptive_card_invoke_action import AdaptiveCardInvokeAction


class AdaptiveCardInvokeValue(CustomBaseModel):
    """
    Defines the structure that arrives in the Activity.Value for Invoke activity with
    Name of 'adaptiveCard/action'.
    """

    action: AdaptiveCardInvokeAction
    "The AdaptiveCardInvokeAction of this adaptive card invoke action value."

    authentication: Optional[AdaptiveCardAuthentication] = None
    "The AdaptiveCardAuthentication for this adaptive card invoke action value."

    state: Optional[str] = None
    "The 'state' or magic code for an OAuth flow."

    trigger: Optional[Literal["manual"]] = None
    "What triggered the action"
