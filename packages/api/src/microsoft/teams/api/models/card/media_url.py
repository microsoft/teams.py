from typing import Optional

from pydantic import BaseModel, Field


class MediaUrl(BaseModel):
    """
    Media URL
    """

    url: str = Field(..., description="Url for the media")
    profile: Optional[str] = Field(
        None,
        description="Optional profile hint to the client to differentiate multiple MediaUrl objects from each other",
    )
