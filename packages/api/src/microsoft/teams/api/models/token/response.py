"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from microsoft.teams.api.models.channel_id import ChannelID
from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class TokenResponse(CustomBaseModel):
    """A response that includes a user token."""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

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
    expiration: str
    """
    The expiration of the token.
    """
    properties: Optional[Dict[str, Any]] = None
    """
    A collection of properties about this response, such as token polling parameters.
    """
