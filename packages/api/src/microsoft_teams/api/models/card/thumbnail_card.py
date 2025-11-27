"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from microsoft_teams.api.models.card.card_image import CardImage
from pydantic import Field

from .basic_card import BasicCard


class ThumbnailCard(BasicCard):
    """
    A thumbnail card (card with a single, small thumbnail image)

    This card type has the same structure as BasicCard but is specifically
    meant to display cards with a single, small thumbnail image.
    """

    # Override parent's default to force explicit choice - users must intentionally
    # provide images=None or images=[...] rather than relying on implicit default
    images: Optional[List[CardImage]] = Field(...)  # pyright: ignore[reportGeneralTypeIssues]
    "Array of thumbnail images for the card (must be explicitly provided)"
