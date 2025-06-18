"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class ThumbnailUrl(CustomBaseModel):
    """
    Thumbnail URL
    """

    url: str
    "URL pointing to the thumbnail to use for media content"
    alt: str
    "HTML alt text to include on this thumbnail image"
