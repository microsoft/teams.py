"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from pydantic import Field

from ..account import TeamsChannelAccount
from ..custom_base_model import CustomBaseModel


class PagedMembersResult(CustomBaseModel):
    """
    Result of a paged members request.
    """

    members: List[TeamsChannelAccount] = Field(default_factory=list[TeamsChannelAccount])
    "The members in this page."

    continuation_token: Optional[str] = None
    "Token to fetch the next page of members. None if this is the last page."
