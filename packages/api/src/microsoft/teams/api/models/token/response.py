"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from microsoft.teams.api.models.channel_id import ChannelID
from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TokenResponse(BaseModel):
    """A response that includes a user token."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    channel_id: Optional[ChannelID] = Field(None, description="The channel ID")
    connection_name: str = Field(..., description="The connection name")
    token: str = Field(..., description="The user token")
    expiration: str = Field(..., description="Expiration for the token, in ISO 8601 format (e.g. '2007-04-05T14:30Z')")
    properties: Optional[Dict[str, Any]] = Field(
        None, description="A collection of properties about this response, such as token polling parameters"
    )
