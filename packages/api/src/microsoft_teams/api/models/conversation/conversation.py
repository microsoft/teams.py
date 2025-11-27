"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from ..account import Account
from ..custom_base_model import CustomBaseModel

ConversationType = Literal["personal", "groupChat"]


class Conversation(CustomBaseModel):
    """Represents a Teams conversation."""

    id: str
    """
    Conversation ID
    """

    tenant_id: Optional[str] = None
    """
    Conversation Tenant ID
    """

    conversation_type: ConversationType
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
