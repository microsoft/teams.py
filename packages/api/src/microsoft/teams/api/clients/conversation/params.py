"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ...models import Account, Activity, Conversation


class GetConversationsParams(BaseModel):
    """Parameters for getting conversations."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    continuation_token: Optional[str] = None


class CreateConversationParams(BaseModel):
    """Parameters for creating a conversation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

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
    activity: Optional[Activity] = None
    """
    The initial activity to post in the conversation.
    """
    channel_data: Optional[Dict[str, Any]] = None
    """
    The channel-specific data for the conversation.
    """


class GetConversationsResponse(BaseModel):
    """Response from getting conversations."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    continuation_token: Optional[str] = None
    """
    Token for getting the next page of conversations.
    """
    conversations: List[Conversation] = []
    """
    List of conversations.
    """
