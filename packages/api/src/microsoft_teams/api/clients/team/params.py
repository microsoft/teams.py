"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List

from ...models import ChannelInfo, CustomBaseModel


class GetTeamConversationsResponse(CustomBaseModel):
    """Response model for getting team conversations."""

    conversations: List[ChannelInfo] = []
    """List of conversations in the team."""
