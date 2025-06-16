from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TeamInfo(BaseModel):
    """
    An interface representing TeamInfo.
    Describes a team
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    id: str = Field(..., description="Unique identifier representing a team")
    name: Optional[str] = Field(None, description="Name of team.")
    aad_group_id: Optional[str] = Field(None, description="The Azure AD Teams group ID.")
