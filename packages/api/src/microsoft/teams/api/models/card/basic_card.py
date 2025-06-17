"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from ..custom_base_model import CustomBaseModel
from .card_action import CardAction
from .card_image import CardImage


class BasicCard(CustomBaseModel):
    """
    A basic card
    """

    title: Optional[str] = None
    "Title of the card"

    subtitle: Optional[str] = None
    "Subtitle of the card"

    text: Optional[str] = None
    "Text for the card"

    images: Optional[List[CardImage]] = None
    "Array of images for the card"

    buttons: Optional[List[CardAction]] = None
    "Set of actions applicable to the current card"

    tap: Optional[CardAction] = None
    "This action will be activated when user taps on the card itself"
