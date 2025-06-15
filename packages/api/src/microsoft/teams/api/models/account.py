"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


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

    id: str = Field(..., description="The unique identifier for the account")
    aad_object_id: Optional[str] = Field(None, description="The Azure AD object ID")
    role: Optional[str] = Field(None, description="The role of the account in the conversation")
    name: Optional[str] = Field(None, description="The display name of the account")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties for the account")
