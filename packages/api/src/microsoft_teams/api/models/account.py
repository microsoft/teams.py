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


class TeamsChannelAccount(CustomBaseModel):
    """
    Represents a Teams channel account, extending the basic channel account with Teams-specific properties.
    This is used to represent a user or bot in Microsoft Teams conversations.
    https://learn.microsoft.com/en-us/dotnet/api/microsoft.bot.schema.teams.teamschannelaccount
    """

    id: str
    """
    Unique identifier for the user or bot in the channel.
    """
    name: Optional[str] = None
    """
    Display-friendly name of the user or bot.
    """
    object_id: Optional[str] = None
    """
    The user's Object ID in Azure Active Directory (AAD).
    """
    role: Optional[AccountRole] = None
    """
    Role of the user (e.g., 'user' or 'bot').
    """
    given_name: Optional[str] = None
    """
    Given name (first name) of the user.
    """
    surname: Optional[str] = None
    """
    Surname (last name) of the user.
    """
    email: Optional[str] = None
    """
    Email address of the user.
    """
    user_principal_name: Optional[str] = None
    """
    Unique User Principal Name (UPN) for the user in AAD.
    """
    tenant_id: Optional[str] = None
    """
    Unique identifier for the user's Azure AD tenant.
    """
    properties: Optional[Dict[str, Any]] = None
    """
    Custom properties associated with the account.
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
