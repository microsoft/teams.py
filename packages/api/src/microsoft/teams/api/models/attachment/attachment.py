from typing import Any, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Attachment(BaseModel):
    """A model representing an attachment."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    id: Optional[str] = Field(None, description="The id of the attachment.")
    content_type: str = Field(..., description="mimetype/Contenttype for the file")
    content_url: Optional[str] = Field(None, description="Content Url")
    content: Optional[Any] = Field(None, description="Embedded content")
    name: Optional[str] = Field(None, description="The name of the attachment")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail associated with attachment")
