"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from microsoft.teams.api.models.channel_id import ChannelID
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TokenResponse(BaseModel):
    """A response that includes a user token."""

    model_config = ConfigDict(
        alias_generator=to_camel,
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
