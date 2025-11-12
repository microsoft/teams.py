"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from .custom_base_model import CustomBaseModel


class MembershipSource(CustomBaseModel):
    """
    Represents the source of a membership.
    """

    id: str
    "The unique identifier for the membership source."

    sourceType: Literal["channel", "team"]
    "The type of roster the user is a member of."

    membershipType: Literal["direct", "transitive"]
    "The user's relationship to the current channel."

    tenantId: str
    "The tenant ID of the user."

    teamGroupId: str
    "The group ID of the team associated with this membership source."
