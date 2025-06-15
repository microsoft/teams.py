"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Conversation(BaseModel):
    """Represents a Teams conversation."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    id: str
    """
    The unique identifier for the conversation.
    """
    type: str
    """
    The type of conversation (e.g., 'channel', 'chat').
    """
    is_group: bool
    """
    Whether this is a group conversation.
    """
    properties: Optional[Dict[str, Any]] = None
    """
    Additional properties for the conversation.
    """
