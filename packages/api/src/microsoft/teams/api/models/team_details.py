"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from .custom_base_model import CustomBaseModel


class TeamDetails(CustomBaseModel):
    """
    Details related to a team.
    """

    id: str
    "Unique identifier representing a team"

    name: Optional[str] = None
    "Name of team."

    type: Literal["standard", "sharedChannel", "privateChannel"]
    "The type of the team. Valid values are standard, sharedChannel and privateChannel."

    aad_group_id: Optional[str] = None
    "Azure Active Directory (AAD) Group Id for the team."

    channel_count: Optional[int] = None
    "Count of channels in the team."

    member_count: Optional[int] = None
    "Count of members in the team."
