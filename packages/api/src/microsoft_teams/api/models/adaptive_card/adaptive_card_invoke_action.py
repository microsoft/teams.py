"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Literal, Optional

from ..custom_base_model import CustomBaseModel


class AdaptiveCardInvokeAction(CustomBaseModel):
    """
    Defines the structure that arrives in the Activity.Value.Action for Invoke
    activity with Name of 'adaptiveCard/action'.
    """

    type: Literal["Action.Execute", "Action.Submit"]
    "The Type of this Adaptive Card Invoke Action."

    id: Optional[str] = None
    "The id of this Adaptive Card Invoke Action."

    verb: Optional[str] = None
    "The verb of this adaptive card action invoke."

    data: Dict[str, Any]
    "The data of this adaptive card action invoke."
