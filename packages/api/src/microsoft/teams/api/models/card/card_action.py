"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ..custom_base_model import CustomBaseModel
from .card_action_type import CardActionType


class CardAction(CustomBaseModel):
    """
    Represents a card action with button properties.
    """

    type: CardActionType
    "The type of action implemented by this button"

    title: str
    "Text description which appears on the button"

    image: Optional[str] = None
    "Image URL which will appear on the button, next to text label"

    text: Optional[str] = None
    "Text for this action"

    display_text: Optional[str] = None
    "(Optional) text to display in the chat feed if the button is clicked"

    value: Any
    "Supplementary parameter for action. Content of this property depends on the ActionType"

    channel_data: Optional[Any] = None
    "Channel-specific data associated with this action"

    image_alt_text: Optional[str] = None
    "Alternate image text to be used in place of the `image` field"
