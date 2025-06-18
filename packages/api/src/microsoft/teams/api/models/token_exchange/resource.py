"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class TokenExchangeResource(CustomBaseModel):
    """Model representing a token exchange resource."""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    id: Optional[str] = None
    """
    The resource ID.
    """
    uri: Optional[str] = None
    """
    The resource URI.
    """
    provider_id: Optional[str] = None
    """
    The provider ID.
    """
