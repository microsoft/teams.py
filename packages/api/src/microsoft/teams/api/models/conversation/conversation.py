"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ..account import Account

ConversationType = Literal["personal", "groupChat"]


class Conversation(BaseModel):
    """Represents a Teams conversation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    id: str
    """
    Conversation ID
    """

    tenant_id: Optional[str] = None
    """
    Conversation Tenant ID
    """

    type: ConversationType
    """
    The Conversations Type
    """

    name: Optional[str] = None
    """
    The Conversations Name
    """

    is_group: Optional[bool] = None
    """
    If the Conversation supports multiple participants
    """

    members: Optional[List[Account]] = None
    """
    List of members in this conversation
    """
