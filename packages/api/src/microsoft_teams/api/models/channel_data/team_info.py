"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from ..team_type import TeamType


class TeamInfo(CustomBaseModel):
    """
    An interface representing TeamInfo.
    Describes a team
    """

    id: Optional[str] = None
    "Unique identifier representing a team"

    name: Optional[str] = None
    "Name of team."

    team_type: Optional[TeamType] = None
    "The type of the team"

    member_count: Optional[int] = None
    "The number of members in the team."

    channel_count: Optional[int] = None
    "The number of channels in the team."

    aad_group_id: Optional[str] = None
    "The Azure AD Teams group ID."
