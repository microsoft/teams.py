"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ...models.conversation import ConversationReference


class TokenExchangeState(BaseModel):
    """State object passed to the bot token service."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    connection_name: str = Field(..., description="The connection name that was used")
    conversation: ConversationReference = Field(..., description="A reference to the conversation")
    relates_to: Optional[ConversationReference] = Field(
        None, description="A reference to a related parent conversation"
    )
    ms_app_id: str = Field(..., description="The URL of the bot messaging endpoint")
