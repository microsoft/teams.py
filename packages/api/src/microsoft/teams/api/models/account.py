"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

AccountRole = Literal["user", "bot"]


class Account(BaseModel):
    """
    Represents a Teams account/user.
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

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
