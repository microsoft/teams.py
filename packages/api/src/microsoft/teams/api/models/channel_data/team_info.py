from typing import Optional

from pydantic import BaseModel, Field


class TeamInfo(BaseModel):
    """
    An interface representing TeamInfo.
    Describes a team
    """

    id: str = Field(..., description="Unique identifier representing a team")
    name: Optional[str] = Field(None, description="Name of team.")
    aad_group_id: Optional[str] = Field(None, alias="aadGroupId", description="The Azure AD Teams group ID.")
