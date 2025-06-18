"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class TokenStatus(CustomBaseModel):
    """The status of a particular token."""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    channel_id: str
    """
    The channel ID.
    """
    connection_name: str
    """
    The connection name.
    """
    has_token: bool
    """
    Boolean indicating if a token is stored for this ConnectionName.
    """
    service_provider_display_name: str
    """
    The display name of the service provider for which this Token belongs to.
    """
