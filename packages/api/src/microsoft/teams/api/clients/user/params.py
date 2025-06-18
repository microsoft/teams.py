"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ...models import ChannelID, TokenExchangeRequest


class GetUserTokenParams(BaseModel):
    """Parameters for getting a user token."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str
    """
    The user ID.
    """
    connection_name: str
    """
    The connection name.
    """
    channel_id: Optional[ChannelID] = None
    """
    The channel ID.
    """
    code: Optional[str] = None
    """
    The authorization code.
    """


class GetUserAADTokenParams(BaseModel):
    """Parameters for getting AAD tokens for a user."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str
    """
    The user ID.
    """
    connection_name: str
    """
    The connection name.
    """
    resource_urls: List[str]
    """
    The resource URLs.
    """
    channel_id: ChannelID
    """
    The channel ID.
    """


class GetUserTokenStatusParams(BaseModel):
    """Parameters for getting token status for a user."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str
    """
    The user ID.
    """
    channel_id: ChannelID
    """
    The channel ID.
    """
    include_filter: str
    """
    The include filter.
    """


class SignOutUserParams(BaseModel):
    """Parameters for signing out a user."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str
    """
    The user ID.
    """
    connection_name: str
    """
    The connection name.
    """
    channel_id: ChannelID
    """
    The channel ID.
    """


class ExchangeUserTokenParams(BaseModel):
    """Parameters for exchanging a user token."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    user_id: str
    """
    The user ID.
    """
    connection_name: str
    """
    The connection name.
    """
    channel_id: ChannelID
    """
    The channel ID.
    """
    exchange_request: TokenExchangeRequest
    """
    The token exchange request.
    """
