"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Optional

from ...models import Account, CustomBaseModel
from .activity import ActivityParams


class CreateConversationParams(CustomBaseModel):
    """Parameters for creating a conversation."""

    members: Optional[List[Account]] = None
    """
    The members to add to the conversation.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID for the conversation.
    """
    activity: Optional[ActivityParams] = None
    """
    The initial activity to post in the conversation.
    """
    channel_data: Optional[Dict[str, Any]] = None
    """
    The channel-specific data for the conversation.
    """
