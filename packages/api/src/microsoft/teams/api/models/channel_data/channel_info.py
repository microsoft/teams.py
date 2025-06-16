from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChannelInfo(BaseModel):
    """
    A channel info object which describes the channel.
    """

    id: str = Field(..., description="Unique identifier representing a channel")
    name: Optional[str] = Field(None, description="Name of the channel")
    type: Optional[Literal["standard", "shared", "private"]] = Field(
        None, description="The type of the channel. Valid values are standard, shared and private."
    )
