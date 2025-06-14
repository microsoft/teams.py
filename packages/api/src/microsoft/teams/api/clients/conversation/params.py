"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ...models import Account, Activity, Conversation


class GetConversationsParams(BaseModel):
    """Parameters for getting conversations."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    continuation_token: Optional[str] = Field(None, description="Token for pagination")


class CreateConversationParams(BaseModel):
    """Parameters for creating a conversation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    is_group: bool = Field(False, description="Whether this is a group conversation")
    bot: Optional[Account] = Field(None, description="Bot account to add to the conversation")
    members: Optional[List[Account]] = Field(None, description="Members to add to the conversation")
    topic_name: Optional[str] = Field(None, description="Topic name for the conversation")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for the conversation")
    activity: Optional[Activity] = Field(None, description="Initial activity to post in the conversation")
    channel_data: Optional[Dict[str, Any]] = Field(None, description="Channel-specific data")


class GetConversationsResponse(BaseModel):
    """Response from getting conversations."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    continuation_token: Optional[str] = Field(None, description="Token for getting the next page of conversations")
    conversations: List[Conversation] = Field([], description="List of conversations")
