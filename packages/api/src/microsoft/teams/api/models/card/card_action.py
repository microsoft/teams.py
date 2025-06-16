from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CardActionType(str, Enum):
    """Available card action types."""

    OPEN_URL = "openUrl"
    IM_BACK = "imBack"
    POST_BACK = "postBack"
    PLAY_AUDIO = "playAudio"
    PLAY_VIDEO = "playVideo"
    SHOW_IMAGE = "showImage"
    DOWNLOAD_FILE = "downloadFile"
    SIGN_IN = "signin"
    CALL = "call"


class CardAction(BaseModel):
    """
    Represents a card action with button properties.
    """

    type: CardActionType = Field(..., description="The type of action implemented by this button")
    title: str = Field(..., description="Text description which appears on the button")
    image: Optional[str] = Field(None, description="Image URL which will appear on the button, next to text label")
    text: Optional[str] = Field(None, description="Text for this action")
    display_text: Optional[str] = Field(
        None, description="(Optional) text to display in the chat feed if the button is clicked", alias="displayText"
    )
    value: Any = Field(
        ..., description="Supplementary parameter for action. Content of this property depends on the ActionType"
    )
    channel_data: Optional[Any] = Field(
        None, description="Channel-specific data associated with this action", alias="channelData"
    )
    image_alt_text: Optional[str] = Field(
        None, description="Alternate image text to be used in place of the `image` field", alias="imageAltText"
    )
