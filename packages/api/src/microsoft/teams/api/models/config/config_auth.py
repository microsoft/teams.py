from typing import Literal, Optional

from pydantic import BaseModel, Field


# Placeholder for external type
class SuggestedActions(BaseModel):
    """Placeholder for SuggestedActions model from ../suggested-actions"""

    pass


class ConfigAuth(BaseModel):
    """
    The bot's authentication config for SuggestedActions
    """

    suggested_actions: Optional[SuggestedActions] = Field(
        None, alias="suggestedActions", description="SuggestedActions for the Bot Config Auth"
    )
    type: Literal["auth"] = Field("auth", description="Type of the Bot Config Auth")
