"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from ...models import ChannelID, CustomBaseModel, TokenExchangeRequest


class GetUserTokenParams(CustomBaseModel):
    """Parameters for getting a user token."""

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


class GetUserAADTokenParams(CustomBaseModel):
    """Parameters for getting AAD tokens for a user."""

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


class GetUserTokenStatusParams(CustomBaseModel):
    """Parameters for getting token status for a user."""

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


class SignOutUserParams(CustomBaseModel):
    """Parameters for signing out a user."""

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


class ExchangeUserTokenParams(CustomBaseModel):
    """Parameters for exchanging a user token."""

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
