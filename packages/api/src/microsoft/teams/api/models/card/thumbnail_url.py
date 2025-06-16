from pydantic import BaseModel, Field


class ThumbnailUrl(BaseModel):
    """
    Thumbnail URL
    """

    url: str = Field(..., description="URL pointing to the thumbnail to use for media content")
    alt: str = Field(..., description="HTML alt text to include on this thumbnail image")
