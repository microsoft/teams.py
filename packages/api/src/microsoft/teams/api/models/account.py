"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Literal, Optional

from .custom_base_model import CustomBaseModel

AccountRole = Literal["user", "bot"]


class Account(CustomBaseModel):
    """
    Represents a Teams account/user.
    """

    id: str
    """
    The unique identifier for the account.
    """
    aad_object_id: Optional[str] = None
    """
    The Azure AD object ID.
    """
    role: Optional[AccountRole] = None
    """
    The role of the account in the conversation.
    """
    properties: Optional[Dict[str, Any]] = None
    """
    Additional properties for the account.
    """
    name: Optional[str] = None
    """
    The name of the account.
    """


class ConversationAccount(CustomBaseModel):
    """
    Represents a Teams conversation account.
    """

    id: str
    """
    The unique identifier for the conversation.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID for the conversation.
    """
    conversation_type: Optional[str] = None
    """
    The type of conversation (personal, groupChat, etc.).
    """
    name: Optional[str] = None
    """
    The name of the conversation.
    """
    is_group: Optional[bool] = None
    """
    Whether this is a group conversation.
    """
