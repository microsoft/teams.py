"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class MediaUrl(CustomBaseModel):
    """
    Media URL
    """

    url: str
    "Url for the media"

    profile: Optional[str] = None
    "Optional profile hint to the client to differentiate multiple MediaUrl objects from each other"
