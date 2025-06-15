"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ..account import Account


class Conversation(BaseModel):
    """Represents a Teams conversation."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    id: str = Field(..., description="The unique identifier for the conversation")
    type: str = Field(..., description="The type of conversation (e.g., 'channel', 'chat')")
    is_group: bool = Field(False, description="Whether this is a group conversation")
    members: Optional[List[Account]] = Field(None, description="The members of the conversation")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties for the conversation")
