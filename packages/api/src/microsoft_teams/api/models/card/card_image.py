"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .card_action import CardAction


class CardImage(CustomBaseModel):
    """
    An image on a card
    """

    url: str
    "URL thumbnail image for major content property"

    alt: Optional[str] = None
    "Image description intended for screen readers"

    tap: Optional[CardAction] = None
    "Action assigned to specific Attachment"
