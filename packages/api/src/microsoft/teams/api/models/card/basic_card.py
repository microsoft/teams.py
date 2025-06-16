from typing import List, Optional

from pydantic import BaseModel, Field

from .card_action import CardAction
from .card_image import CardImage


class BasicCard(BaseModel):
    """
    A basic card
    """

    title: Optional[str] = Field(None, description="Title of the card")
    subtitle: Optional[str] = Field(None, description="Subtitle of the card")
    text: Optional[str] = Field(None, description="Text for the card")
    images: Optional[List[CardImage]] = Field(None, description="Array of images for the card")
    buttons: Optional[List[CardAction]] = Field(None, description="Set of actions applicable to the current card")
    tap: Optional[CardAction] = Field(
        None, description="This action will be activated when user taps on the card itself"
    )
