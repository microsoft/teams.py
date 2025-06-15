"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from microsoft.teams.api.models.channel_id import ChannelID
from microsoft.teams.api.models.token import TokenRequest
from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class GetUserTokenParams(BaseModel):
    """Parameters for getting a user token."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str = Field(..., description="The user ID")
    connection_name: str = Field(..., description="The connection name")
    channel_id: Optional[ChannelID] = Field(None, description="The channel ID")
    code: Optional[str] = Field(None, description="The authorization code")


class GetUserAADTokenParams(BaseModel):
    """Parameters for getting AAD tokens for a user."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str = Field(..., description="The user ID")
    connection_name: str = Field(..., description="The connection name")
    resource_urls: List[str] = Field(..., description="The resource URLs")
    channel_id: ChannelID = Field(..., description="The channel ID")


class GetUserTokenStatusParams(BaseModel):
    """Parameters for getting token status for a user."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str = Field(..., description="The user ID")
    channel_id: ChannelID = Field(..., description="The channel ID")
    include_filter: str = Field(..., description="The include filter")


class SignOutUserParams(BaseModel):
    """Parameters for signing out a user."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str = Field(..., description="The user ID")
    connection_name: str = Field(..., description="The connection name")
    channel_id: ChannelID = Field(..., description="The channel ID")


class ExchangeUserTokenParams(BaseModel):
    """Parameters for exchanging a user token."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str = Field(..., description="The user ID")
    connection_name: str = Field(..., description="The connection name")
    channel_id: ChannelID = Field(..., description="The channel ID")
    exchange_request: TokenRequest = Field(..., description="The token exchange request")
