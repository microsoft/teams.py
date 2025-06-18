"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, List, Optional

from ..custom_base_model import CustomBaseModel
from .card_action import CardAction
from .media_url import MediaUrl
from .thumbnail_url import ThumbnailUrl


class MediaCard(CustomBaseModel):
    """
    Media card
    """

    title: Optional[str] = None
    "Title of this card"

    subtitle: Optional[str] = None
    "Subtitle of this card"

    text: Optional[str] = None
    "Text of this card"

    image: Optional[ThumbnailUrl] = None
    "Thumbnail placeholder"

    media: Optional[List[MediaUrl]] = None
    """
    Media URLs. When this field contains more than one URL,
    each URL is an alt format of the same content.
    """

    buttons: Optional[List[CardAction]] = None
    "Actions on this card"

    shareable: Optional[bool] = None
    "This content may be shared with others (default:true)"

    auto_loop: Optional[bool] = None
    "Should the client loop playback at end of content (default:true)"

    auto_start: Optional[bool] = None
    "Should the client automatically start playback of media in this card (default:true)"

    aspect: Optional[str] = None
    'Aspect ratio of thumbnail/media placeholder. Allowed values are "16:9" and "4:3"'

    duration: Optional[str] = None
    "Length of media content. Formatted as an ISO 8601 Duration field."

    value: Optional[Any] = None
    "Supplementary parameter for this card"
