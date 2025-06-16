from typing import Literal, Optional

from pydantic import BaseModel, Field

from .adaptive_card_invoke_action import AdaptiveCardInvokeAction


# Placeholder
class AdaptiveCardAuthentication(BaseModel):
    """
    Placeholder type.
    Defines the structure that arrives in the Activity.Value.Authentication for Invoke
    activity with Name of 'adaptiveCard/action'.
    """

    pass


class AdaptiveCardInvokeValue(BaseModel):
    """
    Defines the structure that arrives in the Activity.Value for Invoke activity with
    Name of 'adaptiveCard/action'.
    """

    action: AdaptiveCardInvokeAction = Field(
        ..., description="The AdaptiveCardInvokeAction of this adaptive card invoke action value."
    )
    authentication: Optional[AdaptiveCardAuthentication] = Field(
        None, description="The AdaptiveCardAuthentication for this adaptive card invoke action value."
    )
    state: Optional[str] = Field(None, description="The 'state' or magic code for an OAuth flow.")
    trigger: Optional[Literal["manual"]] = Field(None, description="What triggered the action")
