from typing import Any, List, Optional

from pydantic import BaseModel, Field

from .card_action import CardAction
from .media_url import MediaUrl
from .thumbnail_url import ThumbnailUrl



class MediaCard(BaseModel):
    """
    Media card
    """

    title: Optional[str] = Field(None, description="Title of this card")
    subtitle: Optional[str] = Field(None, description="Subtitle of this card")
    text: Optional[str] = Field(None, description="Text of this card")
    image: Optional[ThumbnailUrl] = Field(None, description="Thumbnail placeholder")
    media: Optional[List[MediaUrl]] = Field(
        None,
        description="Media URLs. When this field contains more than one URL, each URL"
        + " is an alt format of the same content.",
    )
    buttons: Optional[List[CardAction]] = Field(None, description="Actions on this card")
    shareable: Optional[bool] = Field(None, description="This content may be shared with others (default:true)")
    auto_loop: Optional[bool] = Field(
        None, description="Should the client loop playback at end of content (default:true)", alias="autoLoop"
    )
    auto_start: Optional[bool] = Field(
        None,
        description="Should the client automatically start playback of media in this card (default:true)",
        alias="autoStart",
    )
    aspect: Optional[str] = Field(
        None, description='Aspect ratio of thumbnail/media placeholder. Allowed values are "16:9" and "4:3"'
    )
    duration: Optional[str] = Field(
        None,
        description="Length of media content. Formatted as an ISO 8601 Duration field.",
    )
    value: Optional[Any] = Field(None, description="Supplementary parameter for this card")
