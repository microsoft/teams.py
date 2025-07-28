"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from microsoft.teams.api.models.channel_id import ChannelID

from ..custom_base_model import CustomBaseModel


class TokenResponse(CustomBaseModel):
    """A response that includes a user token."""

    channel_id: Optional[ChannelID] = None
    """
    The channel ID.
    """
    connection_name: str
    """
    The connection name.
    """
    token: str
    """
    The user token.
    """
    expiration: Optional[str] = None
    """
    The expiration of the token.
    """
    properties: Optional[Dict[str, Any]] = None
    """
    A collection of properties about this response, such as token polling parameters.
    """
