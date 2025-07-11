"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Optional

from ...models import Account, Conversation, CustomBaseModel
from .activity import ActivityParams


class GetConversationsParams(CustomBaseModel):
    """Parameters for getting conversations."""

    continuation_token: Optional[str] = None


class CreateConversationParams(CustomBaseModel):
    """Parameters for creating a conversation."""

    is_group: bool = False
    """
    Whether this is a group conversation.
    """
    bot: Optional[Account] = None
    """
    The bot account to add to the conversation.
    """
    members: Optional[List[Account]] = None
    """
    The members to add to the conversation.
    """
    topic_name: Optional[str] = None
    """
    The topic name for the conversation.
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


class GetConversationsResponse(CustomBaseModel):
    """Response from getting conversations."""

    continuation_token: Optional[str] = None
    """
    Token for getting the next page of conversations.
    """
    conversations: List[Conversation] = []
    """
    List of conversations.
    """
