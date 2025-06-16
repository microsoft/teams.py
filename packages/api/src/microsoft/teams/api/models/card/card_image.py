from typing import Optional

from pydantic import BaseModel, Field

from .card_action import CardAction


class CardImage(BaseModel):
    """
    An image on a card
    """

    url: str = Field(..., description="URL thumbnail image for major content property")
    alt: Optional[str] = Field(None, description="Image description intended for screen readers")
    tap: Optional[CardAction] = Field(None, description="Action assigned to specific Attachment")
