from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class TeamInfo(CustomBaseModel):
    """
    An interface representing TeamInfo.
    Describes a team
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    id: str
    "Unique identifier representing a team"

    name: Optional[str] = None
    "Name of team."

    aad_group_id: Optional[str] = None
    "The Azure AD Teams group ID."
