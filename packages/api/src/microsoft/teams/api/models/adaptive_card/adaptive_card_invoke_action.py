from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class AdaptiveCardInvokeAction(BaseModel):
    """
    Defines the structure that arrives in the Activity.Value.Action for Invoke
    activity with Name of 'adaptiveCard/action'.
    """

    type: Literal["Action.Execute", "Action.Submit"] = Field(
        ..., description="The Type of this Adaptive Card Invoke Action."
    )
    id: Optional[str] = Field(None, description="The id of this Adaptive Card Invoke Action.")
    verb: Optional[str] = Field(None, description="The Verb of this adaptive card action invoke.")
    data: Dict[str, Any] = Field(..., description="The Data of this adaptive card action invoke.")
