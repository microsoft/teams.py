from typing import Any, Optional

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """A model representing an attachment."""

    id: Optional[str] = Field(None, description="The id of the attachment.")
    content_type: str = Field(..., description="mimetype/Contenttype for the file", alias="contentType")
    content_url: Optional[str] = Field(None, description="Content Url", alias="contentUrl")
    content: Optional[Any] = Field(None, description="Embedded content")
    name: Optional[str] = Field(None, description="The name of the attachment")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail associated with attachment", alias="thumbnailUrl")
