"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class TeamInfo(CustomBaseModel):
    """
    An interface representing TeamInfo.
    Describes a team
    """

    id: str
    "Unique identifier representing a team"

    name: Optional[str] = None
    "Name of team."

    team_type: Optional[Literal["standard", "sharedChannel", "privateChannel"]] = None
    "The type of the team"

    member_count: Optional[int] = None
    "The number of members in the team."

    channel_count: Optional[int] = None
    "The number of channels in the team."

    aad_group_id: Optional[str] = None
    "The Azure AD Teams group ID."
