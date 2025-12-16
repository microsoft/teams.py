"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ..custom_base_model import CustomBaseModel


class Attachment(CustomBaseModel):
    """A model representing an attachment."""

    id: Optional[str] = None
    "The id of the attachment."

    content_type: str
    "mimetype/Contenttype for the file"

    content_url: Optional[str] = None
    "Content Url"

    content: Optional[Any] = None
    "Embedded content"

    name: Optional[str] = None
    "The name of the attachment"

    thumbnail_url: Optional[str] = None
    "Thumbnail associated with attachment"
